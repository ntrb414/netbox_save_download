import os
import ipaddress
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result
from nornir.core.plugins.inventory import InventoryPluginRegister
from nornir_utils.plugins.inventory import DictInventory, SimpleInventory
from django.conf import settings
import logging
import yaml
from datetime import datetime

# 注册插件以支持配置格式
try:
    InventoryPluginRegister.register("SimpleInventory", SimpleInventory)
except Exception:
    pass

logger = logging.getLogger('netbox.plugins.netbox_save_download')
BACKUP_PATH = '/opt/config_download'

# 执行 Nornir 备份任务
def run_nornir_backup(devices, username, password):
   # 使用 Nornir 批量执行配置保存并下载
   # 确保备份目录存在,不存在则创建
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
        primary_ip = device.primary_ip4 or device.primary_ip6
        #优先获取设备自身平台，否则获取设备型号平台
        platform = device.platform or device.device_type.platform

        if not primary_ip or not platform:
            continue #跳过没有IP或平台的设备

        hosts[device.name] = {
            "hostname": str(primary_ip.address.ip),
            "username": username,
            "password": password,
            "platform": platform_map.get(platform.slug, 'autodetect'),
        }
    # 检查是否有有效设备
    if not hosts:
        return False, "未找到有效的设备 IP 或平台配置，无法初始化备份任务。"
    # 写入 hosts.yml
    with open("/opt/inventory/hosts.yaml", 'w', encoding="utf-8") as f:
        yaml.dump(hosts, f, allow_unicode=True)
    
    # 写入空的 groups.yml 和 defaults.yml 以防止 SimpleInventory 报错
    for filename in ['groups.yaml', 'defaults.yaml']:
        with open(f"/opt/inventory/{filename}", 'w', encoding='utf-8') as f:
            f.write('{}')

    # 初始化 Nornir (采用用户要求的创建格式)
    inventory = {
        'plugin': 'SimpleInventory',
        'options': {
            'host_file': '/opt/inventory/hosts.yaml',
            'group_file': '/opt/inventory/groups.yaml',
            'defaults_file': '/opt/inventory/defaults.yaml'
        }
    }
    runner = {'plugin': 'threaded', 'options': {'num_workers': 50}}
    logging_config = {'enabled': True, 'level': 'INFO', 'log_file': '/opt/inventory/nornir.log'}

    nr = InitNornir(inventory=inventory, runner=runner, logging=logging_config)
    def backup_task(task_context):
        #Nornir 内部任务：保存并抓取配置
        
        # 1. 执行保存命令
        if 'cisco' in task_context.host.platform:
            task_context.run(task=netmiko_send_command, command_string="write memory")
            output = task_context.run(task=netmiko_send_command, command_string="show running-config")

        elif 'huawei' in task_context.host.platform or 'hp' in task_context.host.platform:
            task_context.run(netmiko_send_command,"save",expect_str = "Y/N") 
            task_context.run(netmiko_send_command,"Y") 
            output = task_context.run(task=netmiko_send_command, command_string="display current-configuration")
        else:
            return "不支持的平台"

        # 2. 写入本地文件 (统一命名为 {hostname}_config.txt 以便下载)
        filename = "{}_config.txt".format(task_context.host.name)
        file_path = os.path.join(BACKUP_PATH, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output.result)
        
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

# 解析 IP 输入
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
