from netbox.plugins import PluginConfig

class SaveDownloadConfig(PluginConfig):
    name = 'netbox_save_download'
    verbose_name = 'NetDevOps 配置备份助手'
    description = '基于 Nornir 的高并发设备配置保存与备份下载工具'
    version = '1.0.0'
    author = 'NetDevOps Team'
    base_url = 'save-download'
    default_settings = {
        'ssh_username': 'admin',
        'ssh_password': 'admin@123',
        'backup_path': '/opt/config_download',
        'threads': 50,
    }

config = SaveDownloadConfig
