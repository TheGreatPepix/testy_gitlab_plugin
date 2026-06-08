from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import Q

from testy.tests_representation.filters.tests import TestWithoutProjectFilter
from testy.tests_representation.models import Test, TestPlan
from testy.utilities.request import mock_request_with_query_params

AUTOMATION_ID = "automation_id"


class TargetResolutionError(ValueError):
    def __init__(self, message: str, missing: dict[str, list[int]] | None = None):
        super().__init__(message)
        self.missing = missing or {}


@dataclass
class ResolvedTargets:
    targets: list[str] = field(default_factory=list)
    test_ids: list[int] = field(default_factory=list)
    case_ids: list[int] = field(default_factory=list)
    plan_ids: list[int] = field(default_factory=list)


def resolve_targets(
    *,
    plan: TestPlan,
    test_ids: list[int] | None = None,
    plan_ids: list[int] | None = None,
    automation_key: str = AUTOMATION_ID,
) -> ResolvedTargets:
    test_ids = _unique_ints(test_ids or [])
    plan_ids = _unique_ints(plan_ids or [])
    if not test_ids and not plan_ids:
        raise TargetResolutionError("Select at least one test or plan.")

    resolved = ResolvedTargets(plan_ids=plan_ids)
    targets: list[str] = []
    missing: dict[str, list[int]] = {}
    selected_plan_ids = _selected_plan_ids(plan=plan, plan_ids=plan_ids, missing=missing)

    tests = _selected_tests(plan=plan, test_ids=test_ids, plan_ids=selected_plan_ids)
    resolved.test_ids = list(tests.values_list("id", flat=True))
    resolved.case_ids = list(tests.values_list("case_id", flat=True))
    found_test_ids = set(resolved.test_ids)
    _add_missing(missing, "tests", [tid for tid in test_ids if tid not in found_test_ids])
    for test in tests:
        target = _automation_value(test.case.attributes, automation_key)
        if target:
            targets.append(target)
        else:
            _add_missing(missing, "tests", [test.id])

    if missing:
        raise TargetResolutionError(
            "Selected items are invalid or do not have automation_id.",
            missing,
        )
    resolved.targets = _unique_strings(targets)
    if not resolved.targets:
        raise TargetResolutionError("Selected items resolved to an empty target list.")
    return resolved


def filter_plan_test_ids(
    *,
    plan: TestPlan,
    filter_conditions: dict | None = None,
    excluded_test_ids: list[int] | None = None,
) -> list[int]:
    plan_ids = plan.get_descendants(include_self=True).values_list("id", flat=True)
    queryset = Test.objects.filter(project=plan.project, plan_id__in=plan_ids)
    if filter_conditions:
        mocked_request = mock_request_with_query_params(filter_conditions)
        filterset = TestWithoutProjectFilter(
            mocked_request.GET, queryset=queryset, request=mocked_request,
        )
        filterset.is_valid()
        queryset = filterset.filter_queryset(queryset)
    if excluded_test_ids:
        queryset = queryset.exclude(id__in=excluded_test_ids)
    return list(queryset.values_list("id", flat=True))


def _selected_plan_ids(
    *, plan: TestPlan, plan_ids: list[int], missing: dict[str, list[int]],
) -> list[int]:
    if not plan_ids:
        return []
    plans = TestPlan.objects.filter(project=plan.project, id__in=plan_ids)
    found_plan_ids = set(plans.values_list("id", flat=True))
    _add_missing(missing, "plans", [pid for pid in plan_ids if pid not in found_plan_ids])
    return list(plans.get_descendants(include_self=True).values_list("id", flat=True))


def _selected_tests(plan: TestPlan, test_ids: list[int], plan_ids: list[int]):
    qs = Test.objects.select_related("case").filter(project=plan.project)
    lookup = Q()
    if test_ids:
        lookup |= Q(id__in=test_ids)
    if plan_ids:
        lookup |= Q(plan_id__in=plan_ids)
    if not lookup:
        return qs.none()
    return qs.filter(lookup).order_by("id")


def _automation_value(attributes: dict | None, key: str) -> str:
    value = (attributes or {}).get(key)
    return str(value).strip() if value else ""


def _unique_ints(values: list[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        item = int(value)
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = value.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _add_missing(missing: dict[str, list[int]], key: str, values: list[int]) -> None:
    if not values:
        return
    bucket = missing.setdefault(key, [])
    for value in values:
        if value not in bucket:
            bucket.append(value)


def plan_automation_readiness(
    plan: TestPlan, automation_key: str = AUTOMATION_ID,
) -> tuple[int, int]:
    plan_ids = (
        TestPlan.objects.filter(id=plan.id)
        .get_descendants(include_self=True)
        .values_list("id", flat=True)
    )
    case_attributes = (
        Test.objects.filter(project=plan.project, plan_id__in=plan_ids)
        .values_list("case__attributes", flat=True)
    )
    total = 0
    missing = 0
    for attributes in case_attributes.iterator():
        total += 1
        if not _automation_value(attributes, automation_key):
            missing += 1
    return total, missing
