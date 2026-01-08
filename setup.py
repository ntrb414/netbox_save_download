from setuptools import setup, find_packages

setup(
    name='netbox-save-download',
    version='0.1',
    description='A NetBox plugin to save and download device configurations',
    install_requires=[
        'netmiko',
        'nornir',
        'nornir_netmiko',
        'nornir_utils',
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
