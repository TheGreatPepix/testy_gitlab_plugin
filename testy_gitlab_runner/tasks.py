from __future__ import annotations

import logging

try:
    from celery import shared_task
except ImportError:
    def shared_task(func=None, **_kwargs):
        return func if func is not None else (lambda wrapped: wrapped)

log = logging.getLogger("testy_gitlab_runner")


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

    @_celery_app.on_after_finalize.connect
    def _register_cleanup_schedule(sender, **_kwargs):
        sender.add_periodic_task(
            crontab(hour=2, minute=30),
            cleanup_history.s(),
            name="testy_gitlab_runner.cleanup_history",
        )
except Exception:
    pass
