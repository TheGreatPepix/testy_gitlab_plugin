from __future__ import annotations

import logging

try:
    from celery import shared_task
except ImportError:
    def shared_task(func=None, **_kwargs):
        return func if func is not None else (lambda wrapped: wrapped)

log = logging.getLogger("testy_gitlab_runner")

def _debounce_seconds() -> int:
    from django.conf import settings
    return int(getattr(settings, "TESTY_GITLAB_RUNNER_NOTIFY_DEBOUNCE", 30))


@shared_task
def finalize_run(run_id):
    from django.utils import timezone

    from testy_gitlab_runner.models import PipelineRun
    from testy_gitlab_runner.services.notifications import notify_run_finished

    run = (
        PipelineRun.objects
        .filter(pk=run_id, notified_at__isnull=True)
        .select_related("connection")
        .first()
    )
    if run is None:
        return

    debounce = _debounce_seconds()
    if run.last_result_at is not None:
        quiet = (timezone.now() - run.last_result_at).total_seconds()
        if quiet < debounce - 10:
            return

    notify_run_finished(run)


def _cleanup_due(run_hour: int, last_run_at, now) -> bool:
    """Due once a day: from ``run_hour`` (UTC) on, unless it already ran since then.

    Comparing with today's slot rather than matching the hour exactly also catches up
    a run missed while beat was down.
    """
    slot = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    return now >= slot and (last_run_at is None or last_run_at < slot)


@shared_task
def cleanup_history():
    from django.utils import timezone

    from testy_gitlab_runner.models import HistoryRetentionPolicy
    from testy_gitlab_runner.services.cleanup import cleanup_project_history

    now = timezone.now()
    for policy in HistoryRetentionPolicy.objects.filter(enabled=True).select_related("project"):
        if not _cleanup_due(policy.run_hour, policy.last_run_at, now):
            continue
        try:
            result = cleanup_project_history(
                policy.project,
                results_days=policy.results_days,
                versions_days=policy.versions_days,
                automation_key=policy.automation_key,
            )
        except Exception as exc:
            log.exception("cleanup_history failed for project %s: %s", policy.project_id, exc)
            continue
        policy.last_run_at = timezone.now()
        policy.last_run_detail = str(result)
        policy.save(update_fields=["last_run_at", "last_run_detail", "updated_at"])
        log.info("cleanup_history project=%s %s", policy.project_id, result)


try:
    from celery import current_app
    from celery.schedules import crontab

    # Register on the app whose autodiscover is importing this module. Neither
    # testy.root.celery.app nor on_after_configure work: `celery -A root` loads
    # root/celery.py as a separate module, i.e. a second app instance, and TestY's
    # celery.py touches app.conf at import, so that signal fires before we connect.
    # Hourly: each project picks its own hour (HistoryRetentionPolicy.run_hour).
    current_app.add_periodic_task(
        crontab(minute=30),
        current_app.signature("testy_gitlab_runner.tasks.cleanup_history"),
        name="testy_gitlab_runner.cleanup_history",
    )
except Exception:
    pass
