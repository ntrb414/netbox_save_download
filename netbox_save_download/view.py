from django.shortcuts import render, redirect
from django.views.generic import View
from django.contrib import messages
from django.http import HttpResponse
from ipam.models import IPAddress
from .utils import run_nornir_backup, parse_ip_input
import os

class SaveDownloadHomeView(View):
    def get(self, request):
        return render(request, 'netbox_save_download/home.html', {
            'found_ips': [],
            'selected_ips': [],
            'ip_input': '',
        })

    def post(self, request):
        action = request.POST.get('action')
        ip_input = request.POST.get('ip_input', '')
        # 从隐藏字段中读取之前识别到的所有 IP
        found_ips = request.POST.getlist('all_found_ips')
        # 从复选框中读取选中的 IP
        selected_ips = request.POST.getlist('selected_ips')

        if action == 'load_ips':
            if ip_input:
                found_ips = parse_ip_input(ip_input)
                selected_ips = found_ips # 默认全部选中
                messages.info(request, f"识别到 {len(found_ips)} 个 IP 地址")
            else:
                messages.error(request, "请输入 IP 地址或范围")

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
                            'ip': ip,
                            'platform': platform_slug
                        })
                    
                    username = "admin"
                    password = "admin@123"
                    
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

        # 无论成功还是报错，都返回 home.html 并携带当前的 found_ips 和 selected_ips
        # 确保即使报错，Identified IP Addresses 列表依然能够通过 found_ips 渲染出来
        return render(request, 'netbox_save_download/home.html', {
            'found_ips': found_ips,
            'selected_ips': selected_ips,
            'ip_input': ip_input,
        })

class DownloadConfigView(View):
    def get(self, request, ip):
        file_path = f"/opt/config_download/{ip}_config.txt"
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{ip}_config.txt"'
            return response
        else:
            messages.error(request, f"未找到 IP {ip} 的备份文件。")
            return redirect('plugins:netbox_save_download:home')
