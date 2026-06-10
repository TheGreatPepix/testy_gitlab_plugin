from django.db import migrations

ACTION_CODE = 1000
VERBOSE_NAME = "Pipeline run finished"
MESSAGE = "Прогон автотестов завершён. {{placeholder}}"


def create_setting(apps, schema_editor):
    NotificationSetting = apps.get_model("core", "NotificationSetting")
    NotificationSetting.objects.update_or_create(
        action_code=ACTION_CODE,
        defaults={"verbose_name": VERBOSE_NAME, "message": MESSAGE},
    )


def remove_setting(apps, schema_editor):
    NotificationSetting = apps.get_model("core", "NotificationSetting")
    NotificationSetting.objects.filter(action_code=ACTION_CODE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("testy_gitlab_runner", "0006_pipelinerun_notify_fields"),
        ("core", "0027_alter_notificationsetting_action_code"),
    ]

    operations = [
        migrations.RunPython(create_setting, remove_setting),
    ]
