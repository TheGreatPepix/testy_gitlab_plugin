from __future__ import annotations

import logging

from django.db.models import Count
from django.utils import timezone

log = logging.getLogger("testy_gitlab_runner")

_PLACEHOLDER = "{{placeholder}}"

RUN_FINISHED_ACTION_CODE = 1000


def _summary_for_run(run) -> tuple[str, int]:
    from testy.tests_representation.models import TestResult

    qs = TestResult.objects.filter(
        project_id=run.connection.project_id,
        attributes__ci_pipeline_url__endswith=f"/pipelines/{run.gitlab_pipeline_id}",
    )
    rows = qs.values("status__name").annotate(n=Count("id")).order_by("-n")

    parts: list[str] = []
    total = 0
    for row in rows:
        parts.append(f"{row['status__name'] or 'Без статуса'}: {row['n']}")
        total += row["n"]
    return (", ".join(parts) if parts else "результатов нет"), total


def notify_run_finished(run) -> None:
    from notifications.signals import notify
    from testy.core.models import NotificationSetting
    from testy.core.services.notifications import NotificationService
    from testy.users.models import User

    model = type(run)
    claimed = model.objects.filter(pk=run.pk, notified_at__isnull=True).update(
        notified_at=timezone.now(),
        status=model.STATUS_FINISHED,
    )
    if not claimed:
        return

    summary, total = _summary_for_run(run)

    recipient = None
    if run.triggered_by:
        recipient = User.objects.filter(username=run.triggered_by).first()
    if recipient is None:
        log.info(
            "gitlab_runner: run %s finished (%s) but no recipient for %r",
            run.pk, summary, run.triggered_by,
        )
        return

    subscribed = NotificationSetting.objects.filter(
        subscribers=recipient,
        action_code=RUN_FINISHED_ACTION_CODE,
    ).exists()
    if not subscribed:
        log.info(
            "gitlab_runner: run %s finished, %s not subscribed — skipping notification",
            run.pk, recipient.username,
        )
        return

    project_id = run.connection.project_id
    if run.plan_id:
        link = f"/projects/{project_id}/plans/{run.plan_id}"
        link_text = "Открыть план"
    else:
        link = f"/projects/{project_id}/plans/"
        link_text = "Открыть проект"

    template = f"Прогон автотестов завершён ({summary}). {_PLACEHOLDER}"

    notify.send(
        recipient,
        recipient=recipient,
        verb=template,
        target=run,
        template=template,
        placeholder_text=link_text,
        placeholder_link=link,
    )
    NotificationService.change_notifications_count(recipient)
    log.info(
        "gitlab_runner: notified %s about run %s (%s results: %s)",
        recipient.username, run.pk, total, summary,
    )
