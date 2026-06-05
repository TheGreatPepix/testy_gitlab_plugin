from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_extend_custom_types_and_custom_attribute'),
        ('testy_gitlab_runner', '0002_pipelinerun_targets'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoryRetentionPolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False)),
                ('results_days', models.PositiveIntegerField(default=90, help_text='Hard-delete autotest results older than this many days (0 = keep).')),
                ('versions_days', models.PositiveIntegerField(default=90, help_text='Delete old case version snapshots older than this many days (0 = keep).')),
                ('automation_key', models.CharField(default='automation_id', help_text='Case attribute that marks a case as an autotest.', max_length=255)),
                ('last_run_at', models.DateTimeField(blank=True, null=True)),
                ('last_run_detail', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='gitlab_retention_policy', to='core.project')),
            ],
            options={
                'verbose_name': 'history retention policy',
                'verbose_name_plural': 'history retention policies',
            },
        ),
    ]
