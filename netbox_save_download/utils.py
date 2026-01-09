import os
import ipaddress
import yaml
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command

BACKUP_PATH = '/opt/config_download'
INVENTORY_PATH = '/opt/inventory'

# 执行 Nornir 备份任务
def run_nornir_backup(devices_data, username, password):
   # 确保必要目录存在
    for path in [BACKUP_PATH, INVENTORY_PATH]:
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                return False, f"无法创建目录 {path}: {str(e)}"

    # 平台映射表
    platform_map = {
        'huawei-vrp': 'huawei',
        'huawei': 'huawei',
        'h3c': 'hp_comware',
    }

    # 构造 Nornir 静态 Inventory 数据
    hosts = {}
    for item in devices_data:
        ip = item['ip']
        nornir_platform = item['platform']
        
        hosts[ip] = {
            "hostname": ip,
            "username": username,
            "password": password,
            "platform": nornir_platform,
        }
    
    # 检查是否有有效设备
    if not hosts:
        return False, "未找到有效的 IP 地址记录，无法初始化备份任务。"
    # 写入 hosts.yaml
    hosts_file = os.path.join(INVENTORY_PATH, "hosts.yaml")
    with open(hosts_file, 'w', encoding="utf-8") as f:
        yaml.safe_dump(hosts, f, allow_unicode=True, default_flow_style=False)
    
    # 写入空的 groups.yaml 和 defaults.yaml
    for filename in ['groups.yaml', 'defaults.yaml']:
        with open(os.path.join(INVENTORY_PATH, filename), 'w', encoding='utf-8') as f:
            f.write('{}')

    # 初始化 Nornir
    inventory = {
        'plugin': 'SimpleInventory',
        'options': {
            'host_file': os.path.join(INVENTORY_PATH, 'hosts.yaml'),
            'group_file': os.path.join(INVENTORY_PATH, 'groups.yaml'),
            'defaults_file': os.path.join(INVENTORY_PATH, 'defaults.yaml')
        }
    }
    runner = {'plugin': 'threaded', 'options': {'num_workers': 50}}
    logging_config = {'enabled': True, 'level': 'INFO', 'log_file': os.path.join(INVENTORY_PATH, 'nornir.log')}

    nr = InitNornir(inventory=inventory, runner=runner, logging=logging_config)
    def backup_task(task_context):
        # Nornir 内部任务：保存并抓取配置
        platform = task_context.host.platform or ""
        output = None
        
        try:
            # 1. 执行保存和抓取命令
            if 'huawei' in platform or 'hp' in platform:
                # 尝试保存，如果失败（例如不需要确认）则继续
                try:
                    task_context.run(netmiko_send_command, command_string="save", expect_str="Y/N")
                    task_context.run(netmiko_send_command, command_string="Y")
                except Exception:
                    pass
                output = task_context.run(task=netmiko_send_command, command_string="display current-configuration")
            
            elif platform == 'autodetect' or not platform:
                # 对于自动检测或未识别平台，尝试通用命令
                # 这里可以扩展更多逻辑，或者直接报错提示
                return "平台未识别或不支持自动备份，请在 NetBox 中正确配置设备平台。"
            else:
                return f"不支持的平台类型: {platform}"

            if output and output.result:
                # 2. 写入本地文件
                filename = "{}_config.txt".format(task_context.host.hostname)
                file_path = os.path.join(BACKUP_PATH, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(output.result)
                return f"备份成功: {file_path}"
            else:
                return "未能获取到配置输出内容"

        except Exception as e:
            return f"备份过程中出错: {str(e)}"

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
