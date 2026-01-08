# NetDevOps 配置备份助手 (NetBox Save & Download Plugin)

这是一个功能强大的 NetBox 插件，旨在通过 Nornir 自动化框架实现大规模网络设备的配置备份与管理。

## 核心功能

- **高并发备份**：基于 Nornir 的多线程引擎，支持同时对 50+ 台设备执行 SSH 配置保存。
- **动态清单导入**：支持通过上传 **CSV 文件**或输入 **IP 地址范围**（CIDR/Range）动态加载待处理设备。
- **本地化存储**：备份文件自动存储在服务器 `/opt/config_download` 目录下，支持随时通过 Web 界面下载。
- **多厂商支持**：内置对 Cisco IOS、Huawei VRP、H3C Comware 等主流网络操作系统的支持。

## 安装步骤

1. **安装依赖**：
   ```bash
   pip install nornir nornir_netmiko nornir_utils netmiko
   ```

2. **安装插件**：
   在插件根目录下运行：
   ```bash
   pip install -e .
   ```

3. **启用插件**：
   在 NetBox 的 `configuration.py` 中：
   ```python
   PLUGINS = [
       'netbox_save_download',
   ]
   ```

4. **系统准备**：
   确保服务器上存在备份目录并具备写权限：
   ```bash
   sudo mkdir -p /opt/config_download
   sudo chown -R netbox:netbox /opt/config_download
   ```

5. **重启服务**：
   ```bash
   sudo systemctl restart netbox netbox-rq
   ```

## 插件配置 (Optional)

在 `configuration.py` 中自定义参数：

```python
PLUGINS_CONFIG = {
    'netbox_save_download': {
        'ssh_username': 'admin',
        'ssh_password': 'password123',
        'backup_path': '/opt/config_download',
        'threads': 50,
    }
}
```

## 使用指南

1. 进入 NetBox 导航栏中的 **配置管理** -> **保存与下载**。
2. 在左侧面板导入设备清单（上传 CSV 或输入 IP 范围）。
3. 检查右侧表格中匹配成功的 NetBox 设备。
4. 勾选设备，点击 **批量执行 Nornir 备份**。
5. 备份成功后，点击 **下载** 按钮获取配置文本。
