import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
        ("tests_representation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="GitlabConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gitlab_url", models.URLField(default="https://gitlab.com")),
                ("gitlab_project_id", models.PositiveIntegerField(
                    help_text="Numeric id of the GitLab project hosting the autotests.")),
                ("ref", models.CharField(default="main", max_length=255,
                                         help_text="Branch or tag to run the pipeline on.")),
                ("trigger_token", models.CharField(max_length=255)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="gitlab_connection", to="core.project")),
            ],
            options={"verbose_name": "GitLab connection"},
        ),
        migrations.CreateModel(
            name="PipelineRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gitlab_pipeline_id", models.PositiveIntegerField(blank=True, null=True)),
                ("web_url", models.URLField(blank=True)),
                ("status", models.CharField(default="triggered", max_length=16)),
                ("case_ids", models.JSONField(blank=True, default=list)),
                ("triggered_by", models.CharField(blank=True, max_length=255)),
                ("detail", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("connection", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="runs", to="testy_gitlab_runner.gitlabconnection")),
                ("plan", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="+", to="tests_representation.testplan")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
