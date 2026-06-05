from django.contrib import admin

from testy_gitlab_runner.models import GitlabConnection, PipelineRun


@admin.register(GitlabConnection)
class GitlabConnectionAdmin(admin.ModelAdmin):
    list_display = ("project", "gitlab_url", "gitlab_project_id", "ref", "enabled")
    list_filter = ("enabled",)


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = ("id", "plan", "gitlab_pipeline_id", "status", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at", "updated_at")
