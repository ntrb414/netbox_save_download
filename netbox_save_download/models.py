from django.db import models
from django.utils import timezone
import uuid
class ScheduledTask(models.Model):
    name = models.CharField(max_length=255)
    job_enbaled = models.BooleanField(default=True)
    id = models.BigAutoField(primary_key=True)
    task_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ip_json = models.TextField(blank=True, null=True,help_text="IP地址列表，每个IP地址占一行")
    interval = models.PositiveIntegerField(default=60)  # 单位：分钟
    start_run_time = models.DateTimeField(null=True, blank=True)  
    next_run_time = models.DateTimeField(null=True, blank=True)

    def schedule_next_run(self):
        now = timezone.now()
        self.start_run_time = now
        self.next_run_time = now + timezone.timedelta(minutes=int(self.interval))
        self.save()
    def __str__(self):
        return f"{self.name}[{self.start_run_time}]"
