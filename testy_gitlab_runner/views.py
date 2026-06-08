from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from testy.core.models import Project
from testy.root.auth.models import TTLToken
from testy.tests_representation.models import TestPlan

from testy_gitlab_runner.models import (
    GitlabConnection,
    HistoryRetentionPolicy,
    PipelineRun,
)
from testy_gitlab_runner.serializers import RunTestsSerializer
from testy_gitlab_runner.services.cleanup import cleanup_project_history
from testy_gitlab_runner.services.runner import trigger_run
from testy_gitlab_runner.services.targets import (
    ResolvedTargets,
    TargetResolutionError,
    filter_plan_test_ids,
    plan_automation_readiness,
    resolve_targets,
)


def _projects():
    return Project.objects.order_by("name")


def _selected_project(request):
    project_id = request.GET.get("project")
    return get_object_or_404(Project, pk=project_id) if project_id else None


def _back(page: str, project_id=None):
    url = reverse(f"plugins:testy_gitlab_runner:{page}")
    if project_id:
        url = f"{url}?project={project_id}"
    return redirect(url)


class ConfigView(View):

    template_name = "testy_gitlab_runner/config.html"

    def get(self, request):
        project = _selected_project(request)
        context = {"projects": _projects(), "project": project, "active": "config"}
        if project:
            context.update(
                connection=GitlabConnection.objects.filter(project=project).first(),
                retention=HistoryRetentionPolicy.objects.filter(project=project).first(),
            )
        return render(request, self.template_name, context)


class TokensView(View):

    template_name = "testy_gitlab_runner/tokens.html"

    def get(self, request):
        project = _selected_project(request)
        return render(request, self.template_name, {
            "projects": _projects(),
            "project": project,
            "active": "tokens",
            "tokens": TTLToken.objects.filter(user=request.user).order_by("-created"),
            "new_token": request.session.pop("new_token", None),
            "new_token_expires": request.session.pop("new_token_expires", None),
        })


class RunsView(View):

    template_name = "testy_gitlab_runner/runs.html"

    def get(self, request):
        project = _selected_project(request)
        context = {"projects": _projects(), "project": project, "active": "runs"}
        if project:
            candidates = (
                TestPlan.objects.filter(project=project, is_archive=False)
                .order_by("-started_at")[:200]
            )
            plans = []
            for plan in candidates:
                total, missing = plan_automation_readiness(plan)
                if total > 0 and missing == 0:
                    plans.append(plan)
                    if len(plans) >= 50:
                        break
            context.update(
                connection=GitlabConnection.objects.filter(project=project).first(),
                plans=plans,
                runs=PipelineRun.objects.filter(connection__project=project)[:20],
            )
        return render(request, self.template_name, context)


class SaveConnectionView(View):

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        connection = (
            GitlabConnection.objects.filter(project=project).first()
            or GitlabConnection(project=project)
        )
        connection.gitlab_url = request.POST["gitlab_url"].strip()
        connection.gitlab_project_id = int(request.POST["gitlab_project_id"])
        connection.ref = request.POST.get("ref", "main").strip() or "main"
        if request.POST.get("trigger_token"):
            connection.trigger_token = request.POST["trigger_token"].strip()
        connection.enabled = bool(request.POST.get("enabled"))
        connection.save()
        messages.success(request, "GitLab connection saved.")
        return _back("index", project.id)


class RetentionConfigView(View):

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        policy, _ = HistoryRetentionPolicy.objects.get_or_create(project=project)
        policy.enabled = bool(request.POST.get("enabled"))
        policy.results_days = int(request.POST.get("results_days") or 0)
        policy.versions_days = int(request.POST.get("versions_days") or 0)
        policy.save()
        messages.success(request, "Retention policy saved.")
        return _back("index", project.id)


class RunCleanupView(View):

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        policy = get_object_or_404(HistoryRetentionPolicy, project=project)
        dry_run = bool(request.POST.get("dry_run"))
        result = cleanup_project_history(
            project,
            results_days=policy.results_days,
            versions_days=policy.versions_days,
            automation_key=policy.automation_key,
            dry_run=dry_run,
        )
        if dry_run:
            messages.success(request, f"Preview (nothing deleted) — would delete: {result}.")
        else:
            policy.last_run_at = timezone.now()
            policy.last_run_detail = str(result)
            policy.save(update_fields=["last_run_at", "last_run_detail", "updated_at"])
            messages.success(request, f"Cleanup done — deleted: {result}.")
        return _back("index", project.id)


class GenerateTokenView(View):

    def post(self, request):
        description = "GitLab autotests (testy_gitlab_runner)"
        project_id = request.POST.get("project")
        project = Project.objects.filter(pk=project_id).first() if project_id else None
        if project:
            description = f"{description} for {project.name}"
        token = TTLToken.objects.create(user=request.user, description=description)
        request.session["new_token"] = token.key
        request.session["new_token_expires"] = f"{token.expiration_date:%Y-%m-%d}"
        return _back("tokens", project_id)


class RevokeTokenView(View):

    def post(self, request, key):
        token = get_object_or_404(TTLToken, key=key, user=request.user)
        token.delete()
        messages.success(request, "TTL token revoked.")
        return _back("tokens", request.POST.get("project"))


class RunView(View):

    def post(self, request):
        plan = get_object_or_404(TestPlan, pk=request.POST["plan_id"])
        connection = get_object_or_404(GitlabConnection, project=plan.project, enabled=True)
        case_ids = request.POST.getlist("case_ids")
        resolved = ResolvedTargets(case_ids=[int(case_id) for case_id in case_ids if case_id])
        run = trigger_run(
            connection, plan, resolved=resolved,
            user=getattr(request.user, "username", ""),
            base_url=request.build_absolute_uri("/"),
        )
        if run.status == PipelineRun.STATUS_ERROR:
            messages.error(request, f"Failed to trigger pipeline: {run.detail}")
        else:
            messages.success(request, f"Pipeline triggered: {run.web_url or run.id}")
        return _back("runs", plan.project_id)


class PlanRunStatusAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id):
        plan = get_object_or_404(TestPlan, pk=plan_id)
        enabled = GitlabConnection.objects.filter(
            project=plan.project, enabled=True,
        ).exists()
        total, missing = plan_automation_readiness(plan)
        return Response(
            {
                "enabled": enabled,
                "total": total,
                "missing": missing,
                "can_run": enabled and total > 0 and missing == 0,
            },
        )


class RunTestsAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RunTestsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.validated_data["plan"]
        connection = get_object_or_404(
            GitlabConnection, project=plan.project, enabled=True,
        )
        test_ids = serializer.validated_data["tests"]
        if serializer.validated_data["all_selected"]:
            test_ids = filter_plan_test_ids(
                plan=plan,
                filter_conditions=serializer.validated_data["filter_conditions"],
                excluded_test_ids=serializer.validated_data["excluded_tests"],
            )
        try:
            resolved = resolve_targets(
                plan=plan,
                test_ids=test_ids,
                plan_ids=serializer.validated_data["plans"],
            )
        except TargetResolutionError as exc:
            return Response(
                {"detail": str(exc), "missing": exc.missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        run = trigger_run(
            connection,
            plan,
            resolved=resolved,
            user=getattr(request.user, "username", ""),
            base_url=request.build_absolute_uri("/"),
        )
        if run.status == PipelineRun.STATUS_ERROR:
            return Response(
                {"detail": run.detail, "id": run.id},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {
                "id": run.id,
                "gitlab_pipeline_id": run.gitlab_pipeline_id,
                "web_url": run.web_url,
                "status": run.status,
                "targets": resolved.targets,
                "tests": resolved.test_ids,
                "plans": resolved.plan_ids,
                "cases": resolved.case_ids,
            },
            status=status.HTTP_201_CREATED,
        )
