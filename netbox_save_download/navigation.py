from netbox.plugins import PluginMenu, PluginMenuGroup, PluginMenuItem

# 定义顶级菜单，使其像 Devices 一样单独显示
menu = PluginMenu(
    label="配置管理",
    icon_class="mdi mdi-cloud-download",  # 设置一个图标
    groups=(
        PluginMenuGroup(
            label="配置备份",
            items=(
                PluginMenuItem(
                    link="plugins:netbox_save_download:home",
                    link_text="保存与下载",
                ),
            ),
        ),
    ),
)
