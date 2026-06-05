from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from testy.tests_description.models import (
    HistoricalTestCase,
    HistoricalTestCaseStep,
    TestCase,
)
from testy.tests_representation.models import TestResult


@dataclass
class CleanupResult:
    results_deleted: int = 0
    versions_deleted: int = 0
    steps_deleted: int = 0

    def __str__(self) -> str:
        return (
            f"results={self.results_deleted}, versions={self.versions_deleted}, "
            f"steps={self.steps_deleted}"
        )


def cleanup_project_history(
    project, *, results_days: int, versions_days: int,
    automation_key: str = "automation_id", dry_run: bool = False,
) -> CleanupResult:
    out = CleanupResult()
    autotest_case_ids = list(
        TestCase.objects.filter(
            project=project, attributes__has_key=automation_key,
        ).values_list("id", flat=True),
    )
    if not autotest_case_ids:
        return out

    if results_days:
        out.results_deleted = _delete_old_results(
            project, autotest_case_ids, results_days, dry_run,
        )
    if versions_days:
        out.versions_deleted, out.steps_deleted = _delete_old_versions(
            autotest_case_ids, versions_days, dry_run,
        )
    return out


def _delete_old_results(project, case_ids, days: int, dry_run: bool) -> int:
    cutoff = timezone.now() - timedelta(days=days)
    qs = TestResult.objects.filter(
        project=project, test__case_id__in=case_ids, created_at__lt=cutoff,
    )
    if dry_run:
        return qs.count()
    deleted, _ = qs.hard_delete()
    return deleted


def _delete_old_versions(case_ids, days: int, dry_run: bool) -> tuple[int, int]:
    cutoff = timezone.now() - timedelta(days=days)

    latest_per_case = set(
        HistoricalTestCase.objects.filter(id__in=case_ids)
        .values("id").annotate(m=Max("history_id")).values_list("m", flat=True),
    )
    referenced = set(
        TestResult.objects.filter(test__case_id__in=case_ids)
        .exclude(test_case_version__isnull=True)
        .values_list("test_case_version", flat=True),
    )
    keep = latest_per_case | referenced

    stale_ids = list(
        HistoricalTestCase.objects.filter(
            id__in=case_ids, history_date__lt=cutoff,
        ).exclude(history_id__in=keep).values_list("history_id", flat=True),
    )
    if not stale_ids:
        return 0, 0

    steps_qs = HistoricalTestCaseStep.objects.filter(test_case_history_id__in=stale_ids)
    versions_qs = HistoricalTestCase.objects.filter(history_id__in=stale_ids)
    if dry_run:
        return versions_qs.count(), steps_qs.count()

    steps_deleted, _ = steps_qs.delete()
    versions_deleted, _ = versions_qs.delete()
    return versions_deleted, steps_deleted
