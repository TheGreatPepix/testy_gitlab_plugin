__version__ = "1.0.4"
default_app_config = "testy_gitlab_runner.apps.TestyGitlabRunnerConfig"

try:
    from testy.plugins.hooks import TestyPluginConfig, hookimpl
except ImportError:
    class TestyPluginConfig:
        pass

    def hookimpl(func):
        return func


class TestyGitlabPluginConfig(TestyPluginConfig):
    package_name = "testy_gitlab_runner"
    verbose_name = "GitLab Autotest Runner"
    description = "Run Python autotests from TestY via GitLab CI/CD."
    version = __version__
    plugin_base_url = "gitlab-runner"
    author = "id.safronov"
    index_reverse_name = "index"
    urls_module = "testy_gitlab_runner.urls"
    min_version = "2.1.3"


@hookimpl
def config():
    return TestyGitlabPluginConfig
