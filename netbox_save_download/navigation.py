from netbox.plugins import PluginMenuItem

# 定义菜单项
home_item = PluginMenuItem(
    link="plugins:netbox_save_download:home",
    link_text="Save and Download Config",
)

# 直接导出 menu_items 元组
menu_items = (home_item,)
