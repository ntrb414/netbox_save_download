from django.db import migrations, models
import django.utils.timezone
import uuid

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduledTask',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('job_enbaled', models.BooleanField(default=True)),
                ('task_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('ip_json', models.TextField(blank=True, help_text='IP地址列表，每个IP地址占一行', null=True)),
                ('interval', models.PositiveIntegerField(default=60)),
                ('start_run_time', models.DateTimeField(blank=True, null=True)),
                ('next_run_time', models.DateTimeField(blank=True, null=True)),
            ],
        ),
    ]
