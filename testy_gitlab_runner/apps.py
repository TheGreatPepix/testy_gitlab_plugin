from django.apps import AppConfig


class TestyGitlabRunnerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "testy_gitlab_runner"
    verbose_name = "GitLab Autotest Runner"

    def ready(self):
        from testy_gitlab_runner import signals  # noqa: F401
