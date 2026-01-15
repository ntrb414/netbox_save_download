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
    # 修复字段名错误: task.ip_json 而不是 task.ips_json
    ips = json.loads(task.ip_json) if task.ip_json else []
    if not ips:
        return

    def job():
        # 1. 构造设备输入数据
        devices = [{ 'name': ip, 'ip': ip } for ip in ips]
        # 2. 执行备份
        run_nornir_backup(devices, username, password)
        # 3. 更新下一次运行时间到数据库，以便前端显示
        try:
            # 重新从数据库获取最新的任务对象
            current_task = ScheduledTask.objects.get(id=task.id)
            current_job = scheduler.get_job(str(current_task.task_id))
            if current_job:
                current_task.next_run_time = current_job.next_run_time
                current_task.save()
        except Exception:
            pass

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