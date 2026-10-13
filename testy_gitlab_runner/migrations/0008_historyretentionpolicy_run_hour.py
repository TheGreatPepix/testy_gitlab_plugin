import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("testy_gitlab_runner", "0007_autotest_run_finished_setting"),
    ]

    operations = [
        migrations.AddField(
            model_name="historyretentionpolicy",
            name="run_hour",
            field=models.PositiveSmallIntegerField(
                default=2,
                help_text="Hour of the day (UTC) to run the scheduled cleanup.",
                validators=[django.core.validators.MaxValueValidator(23)],
            ),
        ),
    ]
