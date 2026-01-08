import os
import csv
import io
import ipaddress
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
from nornir.core.inventory import Inventory
import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger('netbox.plugins.netbox_save_download')
BACKUP_PATH = '/opt/config_download'

def run_nornir_backup(devices, username, password):
    """
    使用 Nornir 批量执行配置保存并下载
    """
    # 确保备份目录存在
    if not os.path.exists(BACKUP_PATH):
        try:
            os.makedirs(BACKUP_PATH)
        except Exception as e:
            return False, f"无法创建备份目录: {str(e)}"

    # 构造 Nornir 静态 Inventory 数据
    # 将 NetBox 的 Device 对象转换为 Nornir Hosts
    hosts = {}
    platform_map = {
        'cisco-ios': 'cisco_ios',
        'huawei-vrp': 'huawei',
        'huawei': 'huawei',
    }

    for device in devices:
        # 适配 NetBox 4.x: 优先获取 IPv4，其次 IPv6
        primary_ip = device.primary_ip4 or device.primary_ip6
        if not primary_ip or not device.platform:
            continue #跳过没有IP或平台的设备
        hosts[device.name] = {
            'hostname': str(primary_ip.address.ip),
            'username': username,
            'password': password,
            'platform': platform_map.get(device.platform.slug, 'autodetect'),
        }

    inventory = {
        'plugin': 'CSVInventory',
        'options': {
            'hosts': hosts,
            'groups': {},
            'defaults': {},
        }
    }

    # 初始化 Nornir (并发数 50)
    nr = InitNornir(
        runner={
            "plugin": "threaded",
            "options": {
                "num_workers": 50,
            },
        },
        inventory=inventory,
        logging={"enabled": False}
    )

    def backup_task(task_context):
        """
        Nornir 内部任务：保存并抓取配置
        """
        # 1. 执行保存命令
        if 'cisco' in task_context.host.platform:
            task_context.run(task=netmiko_send_command, command_string="write memory")
            config = task_context.run(task=netmiko_send_command, command_string="show running-config")

        elif 'huawei' in task_context.host.platform or 'hp' in task_context.host.platform:
            task_context.run(netmiko_send_command,"save",expect_str = "Y/N") 
            task_context.run(netmiko_send_command,"y") 
            config = task_context.run(task=netmiko_send_command, command_string="display current-configuration")
        else:
            return "不支持的平台"

        # 2. 写入本地文件
        filename = "{}.{}.cfg".format(task_context.hostname,datetime.now().strftime("%Y%m%d%H%M%S"))
        file_path = os.path.join(BACKUP_PATH, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(config.result)
        
        return f"备份成功: {file_path}"

    # 执行任务
    try:
        results = nr.run(task=backup_task)
        
        # 统计结果
        success_list = []
        fail_list = []
        for host, result in results.items():
            if result.failed:
                fail_list.append(f"{host}.hostname: {str(result[0].exception or result[0].result)}")
            else:
                success_list.append(host)
        
        return True, {
            'success': success_list,
            'fails': fail_list
        }
    except Exception as e:
        return False, str(e)

def parse_ip_input(ip_text):
    """
    解析 IP 输入，支持:
    - 单个 IP: 192.168.1.1
    - CIDR: 192.168.1.0/24
    - 范围: 192.168.1.1-192.168.1.50
    """
    ips = []
    lines = ip_text.replace(',', '\n').split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            if '-' in line:
                start_ip, end_ip = line.split('-')
                start = ipaddress.IPv4Address(start_ip.strip())
                end = ipaddress.IPv4Address(end_ip.strip())
                for ip_int in range(int(start), int(end) + 1):
                    ips.append(str(ipaddress.IPv4Address(ip_int)))
            elif '/' in line:
                network = ipaddress.IPv4Network(line, strict=False)
                for ip in network.hosts():
                    ips.append(str(ip))
            else:
                ip = ipaddress.IPv4Address(line)
                ips.append(str(ip))
        except Exception as e:
            logger.error(f"解析 IP 失败 {line}: {str(e)}")
            continue
    return list(set(ips))

def parse_csv_file(file_obj):
    """
    从上传的 CSV 文件中提取 IP 地址
    假设 CSV 中有一列名为 'ip' 或第一列即为 IP
    """
    ips = []
    content = file_obj.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    
    # 如果有表头且包含 'ip'
    if 'ip' in reader.fieldnames:
        for row in reader:
            if row['ip']:
                ips.append(row['ip'].strip())
    else:
        # 否则读取第一列
        file_obj.seek(0)
        content = file_obj.read().decode('utf-8')
        simple_reader = csv.reader(io.StringIO(content))
        for row in simple_reader:
            if row and row[0]:
                ips.append(row[0].strip())
    
    return list(set(ips))
