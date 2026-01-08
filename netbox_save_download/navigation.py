from netbox.plugins import PluginMenu, PluginMenuItem

# 定义菜单项
home_item = PluginMenuItem(
    link="plugins:netbox_save_download:home",
    link_text="保存与下载",
)

# 定义顶级菜单 (适配 NetBox 4.x)
# 注意：groups 是一个元组，内部每个元素也是一个元组：("组名", (菜单项列表,))
menu = PluginMenu(
    label="配置管理",
    icon_class="mdi mdi-cloud-download",
    groups=(
        ("配置备份", (home_item,)),
    ),
)
