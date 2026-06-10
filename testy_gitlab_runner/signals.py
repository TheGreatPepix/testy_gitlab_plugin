from __future__ import annotations

import logging
import re

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from testy.tests_representation.models import TestResult

from testy_gitlab_runner.models import PipelineRun
from testy_gitlab_runner.tasks import _debounce_seconds, finalize_run

log = logging.getLogger("testy_gitlab_runner")

_PIPELINE_RE = re.compile(r"/pipelines/(\d+)")


def _schedule_finalize(run_id: int) -> None:
    countdown = _debounce_seconds()
    try:
        finalize_run.apply_async((run_id,), countdown=countdown)
    except AttributeError:
        finalize_run(run_id)


@receiver(post_save, sender=TestResult, dispatch_uid="testy_gitlab_runner_result_notify")
def on_test_result_created(sender, instance, created, **kwargs):
    if not created:
        return

    attributes = instance.attributes or {}
    url = attributes.get("ci_pipeline_url")
    if not url:
        return
    match = _PIPELINE_RE.search(str(url))
    if not match:
        return
    pipeline_id = int(match.group(1))

    run = PipelineRun.objects.filter(
        gitlab_pipeline_id=pipeline_id,
        kind=PipelineRun.KIND_RUN,
        notified_at__isnull=True,
    ).first()
    if run is None:
        return

    PipelineRun.objects.filter(pk=run.pk).update(last_result_at=timezone.now())
    run_pk = run.pk
    transaction.on_commit(lambda: _schedule_finalize(run_pk))
