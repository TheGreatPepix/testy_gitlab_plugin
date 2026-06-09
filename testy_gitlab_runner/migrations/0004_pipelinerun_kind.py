from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testy_gitlab_runner", "0003_historyretentionpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="pipelinerun",
            name="kind",
            field=models.CharField(
                choices=[("run", "Run autotests"), ("sync", "Sync autotests")],
                default="run",
                max_length=16,
            ),
        ),
    ]
