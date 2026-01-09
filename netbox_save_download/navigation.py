from netbox.plugins import PluginMenuItem, PluginMenuGroup

# 定义菜单项
home_item = PluginMenuItem(
    link="plugins:netbox_save_download:home",
    link_text="save and download config",
)

# 定义菜单项组
menu_items = (
    PluginMenuGroup(
        label="config management",
        items=(home_item,),
    ),
)
