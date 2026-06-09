from __future__ import annotations

from django.db import models

from testy.core.models import Project
from testy.tests_representation.models import TestPlan


class GitlabConnection(models.Model):

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="gitlab_connection",
    )
    gitlab_url = models.URLField(default="https://gitlab.com")
    gitlab_project_id = models.PositiveIntegerField(
        help_text="Numeric id of the GitLab project hosting the autotests.",
    )
    ref = models.CharField(max_length=255, default="main",
                           help_text="Branch or tag to run the pipeline on.")
    trigger_token = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "GitLab connection"

    def __str__(self) -> str:
        return f"GitLab[{self.gitlab_project_id}] for project {self.project_id}"


class PipelineRun(models.Model):

    STATUS_TRIGGERED = "triggered"
    STATUS_ERROR = "error"

    KIND_RUN = "run"
    KIND_SYNC = "sync"
    KIND_CHOICES = (
        (KIND_RUN, "Run autotests"),
        (KIND_SYNC, "Sync autotests"),
    )

    connection = models.ForeignKey(
        GitlabConnection, on_delete=models.CASCADE, related_name="runs",
    )
    plan = models.ForeignKey(
        TestPlan, null=True, blank=True, on_delete=models.CASCADE, related_name="+",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_RUN)
    gitlab_pipeline_id = models.PositiveIntegerField(null=True, blank=True)
    web_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, default=STATUS_TRIGGERED)
    case_ids = models.JSONField(default=list, blank=True)
    test_ids = models.JSONField(default=list, blank=True)
    plan_ids = models.JSONField(default=list, blank=True)
    suite_ids = models.JSONField(default=list, blank=True)
    targets = models.JSONField(default=list, blank=True)
    triggered_by = models.CharField(max_length=255, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"PipelineRun #{self.pk} plan={self.plan_id} {self.status}"


class HistoryRetentionPolicy(models.Model):

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="gitlab_retention_policy",
    )
    enabled = models.BooleanField(default=False)
    results_days = models.PositiveIntegerField(
        default=90,
        help_text="Hard-delete autotest results older than this many days (0 = keep).",
    )
    versions_days = models.PositiveIntegerField(
        default=90,
        help_text="Delete old case version snapshots older than this many days (0 = keep).",
    )
    automation_key = models.CharField(
        max_length=255, default="automation_id",
        help_text="Case attribute that marks a case as an autotest.",
    )
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "history retention policy"
        verbose_name_plural = "history retention policies"

    def __str__(self) -> str:
        return f"RetentionPolicy(project={self.project_id}, enabled={self.enabled})"
