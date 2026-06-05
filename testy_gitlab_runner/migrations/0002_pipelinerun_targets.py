from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testy_gitlab_runner", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pipelinerun",
            name="test_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="pipelinerun",
            name="plan_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="pipelinerun",
            name="suite_ids",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="pipelinerun",
            name="targets",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
