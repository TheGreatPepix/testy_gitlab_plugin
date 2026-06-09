import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tests_representation", "0001_initial"),
        ("testy_gitlab_runner", "0004_pipelinerun_kind"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pipelinerun",
            name="plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="tests_representation.testplan",
            ),
        ),
    ]
