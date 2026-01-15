import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from .utils import run_nornir_backup
from .models import ScheduledTask

# 全局调度器,默认20线程
scheduler = BackgroundScheduler(executors={'default': ThreadPoolExecutor(20)})
scheduler.start()

def schedule_backup_task(task: ScheduledTask, username="admin", password="admin@123"):
    ips = json.loads(task.ip_json) if task.ip_json else []
    if not ips:
        return

    def job():
        # 构造设备输入数据
        device_ip = [{ 'ip': ip } for ip in ips]
        run_nornir_backup(device_ip, username, password)

    # 从 start_run_time 开始，以 interval 分钟为间隔循环执行
    scheduler.add_job(
        job,
        'interval',
        minutes=task.interval,
        start_date=task.start_run_time,
        id=str(task.task_id),
        replace_existing=True
    )

def remove_scheduled_backup(task_id):
    try:
        scheduler.remove_job(str(task_id))
    except Exception:
        pass