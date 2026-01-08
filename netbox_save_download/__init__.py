from netbox.plugins import PluginConfig

class SaveDownloadConfig(PluginConfig):
    name = 'netbox_save_download'
    verbose_name = '设备配置保存和备份下载'
    description = '在导航栏增加保存和下载设备配置的按钮'
    version = '0.1'
    base_url = 'save-download'
    default_settings = {
        'ssh_username': 'admin',
        'ssh_password': 'password',
    }

config = SaveDownloadConfig
