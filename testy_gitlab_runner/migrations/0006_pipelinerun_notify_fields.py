from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testy_gitlab_runner", "0005_pipelinerun_plan_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="pipelinerun",
            name="last_result_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pipelinerun",
            name="notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
