from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from ipam.models import IPAddress
from .utils import run_nornir_backup, parse_ip_input, parse_csv_file
import os
import datetime 
from .utils import read_ip_file 
from .models import ScheduledTask
from .schedule import schedule_backup_task, remove_scheduled_backup
import json

class SaveDownloadHomeView(View):
    def get(self, request):
        tasks = ScheduledTask.objects.all().order_by('-start_run_time')
        return render(request, 'netbox_save_download/home.html', {
            'found_ips': [],
            'selected_ips': [],
            'ip_input': '',
            'tasks': tasks,
        })
    def post(self, request):
        action = request.POST.get('action')
        ip_input = request.POST.get('ip_input', '')
        ip_csv_file = request.FILES.get('ip_csv_file')
        # 从隐藏字段中读取之前识别到的所有 IP
        found_ips = request.POST.getlist('all_found_ips')
        # 从复选框中读取选中的 IP
        selected_ips = request.POST.getlist('selected_ips')

        if action == 'load_ips':
            found_ips = []
            if ip_input:
            # 1. 解析输入
                parsed_ips = parse_ip_input(ip_input)
            
            # 2. 读取文件现有内容用于查重
                existing_ips = set()
                if os.path.exists('/opt/save_IPs.txt'):
                    with open('/opt/save_IPs.txt', 'r', encoding='utf-8') as f:
                        existing_ips = {line.strip() for line in f}
            
            # 3. 过滤并写入新 IP
                new_ips = [ip for ip in parsed_ips if ip not in existing_ips]
                if new_ips:
                    with open('/opt/save_IPs.txt', 'a', encoding='utf-8') as f:
                        for ip in new_ips:
                            f.write(ip + '\n')
            
                found_ips = parsed_ips # 返回给前端显示
            # 处理 CSV 文件上传
            if ip_csv_file:
                try:
                    found_ips.extend(parse_csv_file(ip_csv_file))
                except Exception as e:
                    messages.error(request, f"解析 CSV 文件出错: {str(e)}")
            
            if found_ips:
                found_ips = list(set(found_ips)) # 去重
                selected_ips = found_ips # 默认全部选中
                messages.info(request, f"识别到 {len(found_ips)} 个 IP 地址")
            else:
                messages.error(request, "请输入 IP 地址或上传 CSV 文件")

        elif action == 'save':
            # 如果隐藏字段丢失（例如页面过期），尝试从输入框重新解析以保持列表显示
            if not found_ips and ip_input:
                found_ips = parse_ip_input(ip_input)

            if selected_ips:
                try:
                    devices_data = []
                    for ip in selected_ips:
                        # 尝试从 NetBox 获取平台信息作为参考
                        platform_slug = None
                        try:
                            ip_obj = IPAddress.objects.filter(address__host=ip).first()
                            if ip_obj and ip_obj.assigned_object and hasattr(ip_obj.assigned_object, 'platform') and ip_obj.assigned_object.platform:
                                platform_slug = ip_obj.assigned_object.platform.slug
                        except Exception:
                            pass
                        
                        devices_data.append({
                                'name': ip,
                                'ip': ip,
                                'platform': platform_slug
                            })
                    
                    username = "admin"
                    password = "123456"
                    
                    success, result = run_nornir_backup(devices_data, username, password)
                    
                    if success:
                        success_count = len(result['success'])
                        if success_count:
                            messages.success(request, f"Nornir 任务完成: 成功 {success_count} 台")
                        for fail_msg in result['fails']:
                            messages.error(request, fail_msg)
                    else:
                        messages.error(request, f"Nornir 运行失败: {result}")
                except Exception as e:
                    messages.error(request, f"执行备份时发生意外错误: {str(e)}")
            else:
                messages.error(request, "请先勾选要执行任务的 IP")

        elif action == 'start_backup':
            # 从表单传递数据中，收集定时任务参数
            name = request.POST.get('scheduled_task_name')
            start_run_time_str = request.POST.get('scheduled_start')
            interval_str = request.POST.get('scheduled_interval')
            ips = request.POST.getlist('scheduled_task_ips')

            try:
                # 1. 校验必填字段
                if not name or not interval_str:
                    raise ValueError("任务名称和执行间隔为必填项")
                
                interval = int(interval_str)

                # 2. 解析时间 (兼容浏览器可能发送的 'T' 分隔符)
                if start_run_time_str:
                    # 替换 T 为空格以匹配 strptime 格式，或者尝试多种格式
                    start_run_time_str = start_run_time_str.replace('T', ' ')
                    try:
                        start_run_time = datetime.datetime.strptime(start_run_time_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        # 尝试带秒的格式
                        start_run_time = datetime.datetime.strptime(start_run_time_str, '%Y-%m-%d %H:%M:%S')
                else:
                    start_run_time = datetime.datetime.now()

                # 3. 处理 IP 列表
                if not ips:
                    messages.warning(request, "未选择 IP 地址，将从 /opt/save_IPs.txt 读取")
                    ips = read_ip_file()
                
                if not ips:
                    raise ValueError("无可用的 IP 地址来创建任务")

                # 4. 创建定时任务模型
                task = ScheduledTask.objects.create(
                    name=name,
                    ip_json=json.dumps(ips),
                    interval=interval,
                    start_run_time=start_run_time
                )

                # 5. 注册到调度器 (APScheduler)
                schedule_backup_task(task)
                
                messages.success(request, f"定时任务 '{name}' 已成功创建并启动！开始时间: {start_run_time}")

            except Exception as e:
                messages.error(request, f"创建定时任务失败: {str(e)}")

        elif action == 'delete_task':
            task_id = request.POST.get('task_db_id')
            try:
                task = ScheduledTask.objects.get(id=task_id)
                # 1. 从调度器移除
                remove_scheduled_backup(task.task_id)
                # 2. 从数据库移除
                task_name = task.name
                task.delete()
                messages.success(request, f"定时任务 '{task_name}' 已成功删除。")
            except ScheduledTask.DoesNotExist:
                messages.error(request, "任务不存在，可能已被删除。")
            except Exception as e:
                messages.error(request, f"删除任务失败: {str(e)}")

        # 无论成功还是报错，都返回 home.html 并携带当前的 found_ips 和 selected_ips
        tasks = ScheduledTask.objects.all().order_by('-start_run_time')
        return render(request, 'netbox_save_download/home.html', {
            'found_ips': found_ips,
            'selected_ips': selected_ips,
            'ip_input': ip_input,
            'tasks': tasks,
        })

class ReadIPFileView(View):
    def get(self, request):
        ip_list = read_ip_file()
        return JsonResponse(ip_list, safe=False)

class DownloadConfigView(View):
    def get(self, request, ip):
        file_path = f"/opt/config_download/{datetime.datetime.now().strftime('%Y%m%d')}/{ip}_config.txt"
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{ip}_config.txt"'
            return response
        else:
            messages.error(request, f"未找到 IP {ip} 的备份文件。")
            return redirect('plugins:netbox_save_download:home')

