# NetBox Save & Download Plugin

一个用于 NetBox 的插件，在导航栏增加保存和下载设备配置的按钮。

## 功能

- 在左侧导航栏增加独立的“配置管理”菜单。
- 支持通过 SSH 实时保存和备份下载设备配置（需配合 netmiko）。

## 安装

1. 将插件目录拷贝到 NetBox 所在的服务器。
2. 进入插件目录并安装：
   ```bash
   pip install .
   ```
3. 在 NetBox 的 `configuration.py` 中启用插件：
   ```python
   PLUGINS = [
       'netbox_save_download',
   ]
   ```
4. 重启 NetBox 服务。

## 配置

你可以在 `configuration.py` 的 `PLUGINS_CONFIG` 中定义默认的 SSH 凭据：

```python
PLUGINS_CONFIG = {
    'netbox_save_download': {
        'ssh_username': 'admin',
        'ssh_password': 'password',
    }
}
```
