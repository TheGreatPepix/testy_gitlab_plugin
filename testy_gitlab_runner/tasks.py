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


@shared_task
def cleanup_history():
    from django.utils import timezone

    from testy_gitlab_runner.models import HistoryRetentionPolicy
    from testy_gitlab_runner.services.cleanup import cleanup_project_history

    for policy in HistoryRetentionPolicy.objects.filter(enabled=True).select_related("project"):
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
    from celery.schedules import crontab

    from testy.root.celery import app as _celery_app

    @_celery_app.on_after_configure.connect
    def _register_cleanup_schedule(sender, **_kwargs):
        schedule = dict(sender.conf.beat_schedule or {})
        schedule.setdefault(
            "testy_gitlab_runner.cleanup_history",
            {
                "task": "testy_gitlab_runner.tasks.cleanup_history",
                "schedule": crontab(hour=2, minute=30),
            },
        )
        sender.conf.beat_schedule = schedule
except Exception:
    pass
