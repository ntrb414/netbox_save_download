from netbox.plugins import PluginMenu, PluginMenuItem

# 定义菜单项
home_item = PluginMenuItem(
    link="plugins:netbox_save_download:home",
    link_text="save and download config",
)

# 定义顶级菜单
menu = PluginMenu(
    label="config management",
    icon_class="mdi mdi-cloud-download",
    groups=(
        ("save and download config", (home_item,)),
    ),
)
