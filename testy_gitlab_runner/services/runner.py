from __future__ import annotations

import json

from django.conf import settings

from testy_gitlab_runner.models import GitlabConnection, PipelineRun
from testy_gitlab_runner.services.gitlab_client import GitlabClient, GitlabError
from testy_gitlab_runner.services.targets import ResolvedTargets


def build_pipeline_variables(
    connection: GitlabConnection,
    plan,
    resolved: ResolvedTargets,
    base_url: str = "",
    mode: str = "run",
) -> dict[str, str]:
    testy_base = (getattr(settings, "TESTY_PUBLIC_URL", "") or base_url).rstrip("/")
    variables = {
        "TESTY_ENABLED": "1",
        "TESTY_MODE": mode,
        "TESTY_URL": testy_base,
        "TESTY_PROJECT_ID": str(connection.project_id),
    }
    if plan is not None:
        variables["TESTY_PLAN_ID"] = str(plan.id)
    if resolved.targets:
        variables["TESTY_PYTEST_TARGETS"] = json.dumps(
            resolved.targets, ensure_ascii=False,
        )
    if resolved.target_map:
        variables["TESTY_TEST_MAP"] = json.dumps(
            resolved.target_map, ensure_ascii=False,
        )
    return variables


def _trigger(
    connection: GitlabConnection,
    plan,
    *,
    resolved: ResolvedTargets,
    kind: str,
    mode: str,
    user: str,
    base_url: str,
) -> PipelineRun:
    run = PipelineRun.objects.create(
        connection=connection,
        plan=plan,
        kind=kind,
        case_ids=resolved.case_ids,
        test_ids=resolved.test_ids,
        plan_ids=resolved.plan_ids,
        targets=resolved.targets,
        triggered_by=str(user), status=PipelineRun.STATUS_TRIGGERED,
    )
    client = GitlabClient(connection.gitlab_url, connection.gitlab_project_id)
    try:
        pipeline = client.trigger_pipeline(
            trigger_token=connection.trigger_token,
            ref=connection.ref,
            variables=build_pipeline_variables(connection, plan, resolved, base_url, mode),
        )
    except GitlabError as exc:
        run.status = PipelineRun.STATUS_ERROR
        run.detail = str(exc)
        run.save(update_fields=["status", "detail", "updated_at"])
        return run

    run.gitlab_pipeline_id = pipeline.id
    run.web_url = pipeline.web_url
    run.save(update_fields=["gitlab_pipeline_id", "web_url", "updated_at"])
    return run


def trigger_run(
    connection: GitlabConnection, plan, *, resolved: ResolvedTargets, user="", base_url="",
) -> PipelineRun:
    return _trigger(
        connection, plan, resolved=resolved,
        kind=PipelineRun.KIND_RUN, mode="run", user=user, base_url=base_url,
    )


def trigger_sync(
    connection: GitlabConnection, *, user="", base_url="",
) -> PipelineRun:
    return _trigger(
        connection, None, resolved=ResolvedTargets(),
        kind=PipelineRun.KIND_SYNC, mode="sync", user=user, base_url=base_url,
    )
