import os
import ipaddress
import yaml
import logging
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command

logger = logging.getLogger('netbox.plugins.netbox_save_download')

# 动态获取备份路径
def get_backup_path():
    from django.conf import settings
    plugin_config = settings.PLUGINS_CONFIG.get('netbox_save_download', {})
    path = plugin_config.get('backup_path', '/opt/config_download')
    return path

# 执行 Nornir 备份任务
def run_nornir_backup(selected_devices, username, password):
    BACKUP_PATH = get_backup_path()
    INVENTORY_PATH = '/tmp/nornir_inventory' # 使用临时目录避免权限冲突

    # 确保目录存在
    for path in [BACKUP_PATH, INVENTORY_PATH]:
        if not os.path.exists(path):
            try:
                os.makedirs(path, mode=0o775, exist_ok=True)
            except Exception as e:
                return False, f"无法创建目录 {path}: {str(e)}"

    # 平台映射表 (NetBox Slug -> Netmiko Platform)
    platform_map = {
        'huawei-vrp': 'huawei',
        'huawei': 'huawei',
        'h3c': 'hp_comware',
        'cisco-ios': 'cisco_ios',
        'cisco': 'cisco_ios',
    }

    # 构造 Nornir 静态 Inventory 数据
    hosts = {}
    for device in selected_devices:
        # 获取管理 IP
        ip = str(device.primary_ip4.address.ip) if device.primary_ip4 else None
        if not ip:
            continue
            
        # 获取平台映射
        platform_slug = device.platform.slug if device.platform else 'generic'
        nornir_platform = platform_map.get(platform_slug, 'autodetect')
        
        hosts[device.name] = {
            "hostname": ip,
            "username": username,
            "password": password,
            "platform": nornir_platform,
        }
    
    if not hosts:
        return False, "选中的设备中没有配置主 IPv4 地址，无法备份。"

    # 写入 Inventory 文件
    hosts_file = os.path.join(INVENTORY_PATH, "hosts.yaml")
    with open(hosts_file, 'w', encoding="utf-8") as f:
        yaml.safe_dump(hosts, f, allow_unicode=True)
    
    with open(os.path.join(INVENTORY_PATH, 'groups.yaml'), 'w') as f: f.write('{}')
    with open(os.path.join(INVENTORY_PATH, 'defaults.yaml'), 'w') as f: f.write('{}')

    # 初始化 Nornir
    inventory = {
        'plugin': 'SimpleInventory',
        'options': {
            'host_file': os.path.join(INVENTORY_PATH, 'hosts.yaml'),
            'group_file': os.path.join(INVENTORY_PATH, 'groups.yaml'),
            'defaults_file': os.path.join(INVENTORY_PATH, 'defaults.yaml')
        }
    }
    nr = InitNornir(inventory=inventory, runner={'plugin': 'threaded', 'options': {'num_workers': 20}})

    def backup_task(task):
        # 1. 执行备份命令
        if 'huawei' in task.host.platform or 'hp' in task.host.platform:
            # 华为/H3C 保存配置
            try:
                task.run(netmiko_send_command, command_string="save", expect_str=r"[Y/N]")
                task.run(netmiko_send_command, command_string="Y")
            except:
                pass
            cmd = "display saved-configuration"
        elif 'cisco' in task.host.platform:
            cmd = "show running-config"
        else:
            raise Exception(f"暂不支持的平台: {task.host.platform}")

        result = task.run(netmiko_send_command, command_string=cmd)
        
        if not result.result:
            raise Exception("未能获取到配置内容")

        # 2. 写入文件
        file_path = os.path.join(BACKUP_PATH, f"{task.host.name}_config.txt")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.result)
        except Exception as e:
            raise Exception(f"文件写入失败: {str(e)}")
            
        return f"备份已保存至 {file_path}"

    # 运行任务
    results = nr.run(task=backup_task)
    
    success_list = []
    fail_list = []
    for host, result in results.items():
        if result.failed:
            # 获取底层的错误信息
            err = result[0].result if result[0].result else "未知错误"
            if result[0].exception:
                err = str(result[0].exception)
            fail_list.append(f"设备 {host} 失败: {err}")
        else:
            success_list.append(host)
    
    return True, {'success': success_list, 'fails': fail_list}

# 解析 IP 输入
def parse_ip_input(ip_text):
    ips = []
    for line in ip_text.replace(',', '\n').split('\n'):
        line = line.strip()
        if not line: continue
        try:
            if '-' in line:
                start_ip, end_ip = line.split('-')
                start = ipaddress.IPv4Address(start_ip.strip())
                end = ipaddress.IPv4Address(end_ip.strip())
                for ip_int in range(int(start), int(end) + 1):
                    ips.append(str(ipaddress.IPv4Address(ip_int)))
            elif '/' in line:
                ips.extend([str(ip) for ip in ipaddress.IPv4Network(line, strict=False).hosts()])
            else:
                ips.append(str(ipaddress.IPv4Address(line)))
        except:
            continue
    return list(set(ips))

# 解析 CSV (简单实现)
def parse_csv_file(csv_file):
    import csv
    import io
    ips = []
    file_data = csv_file.read().decode('utf-8')
    reader = csv.reader(io.StringIO(file_data))
    for row in reader:
        for cell in row:
            if cell.strip():
                ips.extend(parse_ip_input(cell.strip()))
    return list(set(ips))
