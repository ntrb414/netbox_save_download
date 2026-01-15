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
        # 1. 立即更新下一次运行时间到数据库 (任务开始时就更新，给用户即时反馈)
        try:
            current_task = ScheduledTask.objects.get(id=task.id)
            current_job = scheduler.get_job(str(current_task.task_id))
            if current_job:
                current_task.next_run_time = current_job.next_run_time
                current_task.save()
        except Exception as e:
            print(f"Update next_run_time failed: {e}")

        # 2. 构造设备输入数据并执行备份
        try:
            devices = [{ 'name': ip, 'ip': ip } for ip in ips]
            run_nornir_backup(devices, username, password)
        except Exception as e:
            print(f"Run backup failed: {e}")

    # 从 start_run_time 开始，以 interval 分钟为间隔循环执行
    job_instance = scheduler.add_job(
        job,
        'interval',
        minutes=task.interval,
        start_date=task.start_run_time,
        id=str(task.task_id),
        replace_existing=True
    )
    
    # 初始创建时，更新一次下一次运行时间
    task.next_run_time = job_instance.next_run_time
    task.save()

def remove_scheduled_backup(task_id):
    try:
        scheduler.remove_job(str(task_id))
    except Exception:
        pass