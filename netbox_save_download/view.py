from django.shortcuts import render, get_object_or_404
from django.views.generic import View
from django.contrib import messages
from django.http import HttpResponse
from dcim.models import Device
from .utils import run_nornir_backup, parse_ip_input, parse_csv_file
import os

class SaveDownloadHomeView(View):
    def get(self, request):
        # 默认不显示任何设备，等待用户输入
        return render(request, 'netbox_save_download/home.html', {
            'devices': [],
        })

    def post(self, request):
        action = request.POST.get('action')
        devices = []
        found_ips = []

        # 1. 处理 CSV 加载
        if action == 'load_csv':
            csv_file = request.FILES.get('csv_file')
            if csv_file:
                found_ips = parse_csv_file(csv_file)
                messages.info(request, f"从 CSV 中识别到 {len(found_ips)} 个 IP 地址")
            else:
                messages.error(request, "请先选择要上传的 CSV 文件")

        # 2. 处理 IP 范围输入加载
        elif action == 'load_ips':
            ip_input = request.POST.get('ip_input')
            if ip_input:
                found_ips = parse_ip_input(ip_input)
                messages.info(request, f"识别到 {len(found_ips)} 个有效 IP 地址")
            else:
                messages.error(request, "请输入 IP 地址或范围")

        # 3. 根据 IP 查找 NetBox 设备
        if found_ips:
            # 在 NetBox 中查找主 IP 匹配这些地址的设备
            devices = Device.objects.filter(
                primary_ip__address__host__in=found_ips,
                platform__isnull=False
            ).distinct()
            
            if not devices:
                messages.warning(request, "未在 NetBox 中找到与输入 IP 匹配的设备（且需具备平台定义）")
            else:
                messages.success(request, f"成功匹配到 {devices.count()} 台 NetBox 设备")

        # 4. 执行 Nornir 备份操作 (逻辑保持不变，但基于当前显示的 devices)
        elif action == 'save':
            device_ids = request.POST.getlist('pk')
            if device_ids:
                selected_devices = Device.objects.filter(pk__in=device_ids)
                username = "admin" 
                password = "password123"
                
                success, result = run_nornir_backup(selected_devices, username, password)
                
                if success:
                    success_count = len(result['success'])
                    if success_count:
                        messages.success(request, f"Nornir 并发备份成功: {success_count} 台设备。文件已保存至 /opt/config_download")
                    for fail_msg in result['fails']:
                        messages.error(request, fail_msg)
                else:
                    messages.error(request, f"Nornir 运行出错: {result}")
                
                # 重新加载这些设备以保持列表显示
                devices = selected_devices
            else:
                messages.error(request, "请先勾选要备份的设备")

        return render(request, 'netbox_save_download/home.html', {
            'devices': devices,
        })

class DownloadConfigView(View):
    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        file_path = f"/opt/config_download/{device.name}_config.txt"
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{device.name}_config.txt"'
            return response
        else:
            messages.error(request, f"未找到备份文件，请先执行备份操作。")
            return render(request, 'netbox_save_download/home.html', {'devices': []})
