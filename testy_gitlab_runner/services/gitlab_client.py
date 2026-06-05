from __future__ import annotations

from dataclasses import dataclass

import requests


class GitlabError(Exception):
    pass


@dataclass
class TriggeredPipeline:
    id: int
    status: str
    web_url: str


class GitlabClient:
    def __init__(self, base_url: str, project_id: int, timeout: int = 30):
        self.base = base_url.rstrip("/")
        self.project_id = project_id
        self.timeout = timeout

    @property
    def _project_api(self) -> str:
        return f"{self.base}/api/v4/projects/{self.project_id}"

    def trigger_pipeline(
        self, trigger_token: str, ref: str, variables: dict[str, str],
    ) -> TriggeredPipeline:
        data = {"token": trigger_token, "ref": ref}
        for key, value in variables.items():
            data[f"variables[{key}]"] = value
        try:
            resp = requests.post(
                f"{self._project_api}/trigger/pipeline", data=data, timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise GitlabError(f"trigger request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise GitlabError(f"trigger failed: {resp.status_code} {resp.text[:500]}")
        body = resp.json()
        return TriggeredPipeline(
            id=body["id"], status=body.get("status", "created"),
            web_url=body.get("web_url", ""),
        )
