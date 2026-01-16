# NetBox Save Download Plugin

A NetBox plugin for automated network device configuration backup and download management using Nornir.

## Features

- **Configuration Backup**: Automate network device configuration backups using Nornir
- **IP Management**: Support for manual IP input and CSV file upload
- **Scheduled Tasks**: Create and manage scheduled backup tasks with customizable intervals
- **Download Management**: Download configuration files directly from the web interface
- **NetBox Integration**: Seamlessly integrates with NetBox IPAM data

## Installation

1. Install the plugin:
```bash
pip install netbox-save-download
```

2. Add the plugin to your NetBox configuration (`configuration.py`):
```python
PLUGINS = [
    'netbox_save_download',
]

PLUGINS_CONFIG = {
    'netbox_save_download': {
        'backup_path': '/opt/config_download',  # Default backup directory
    }
}
```

3. Run database migrations:
```bash
python manage.py migrate
```

4. Restart NetBox services.

## Usage

### Manual Backup

1. Navigate to the plugin homepage in NetBox
2. Enter IP addresses manually or upload a CSV file
3. Select the devices you want to back up
4. Click "Save" to execute the backup immediately

### Scheduled Backups

1. Load IP addresses as described above
2. Click "Start Backup" to create a scheduled task
3. Configure:
   - Task name
   - Start time
   - Execution interval (in minutes)
   - Target IP addresses
4. The task will be automatically scheduled and executed

### Downloading Configurations

1. View the list of scheduled tasks on the plugin homepage
2. Click the download button next to any device to retrieve its configuration file
3. The plugin will search for the most recent backup (within the last 7 days)

## File Structure

```
netbox_save_download/
├── __init__.py
├── models.py              # Database models for scheduled tasks
├── view.py                # Main application views
├── urls.py                # URL routing
├── utils.py               # Backup utilities and Nornir integration
├── utils_with_log.py      # Enhanced utilities with logging
├── schedule.py            # Task scheduling functionality
├── migrations/            # Database migrations
├── templates/             # HTML templates
│   └── netbox_save_download/
│       └── home.html
└── tests/                 # Test files
```

## Configuration

### Plugin Configuration Options

- `backup_path`: Directory path where configuration backups are stored (default: `/opt/config_download`)

### Required Files

- `/opt/save_IPs.txt`: File for storing IP addresses (automatically managed)

## Dependencies

- NetBox
- Django
- Nornir
- APScheduler (for scheduled tasks)

## API Endpoints

- `GET /`: Main plugin interface
- `GET /download/<ip>/`: Download configuration for specific IP
- `GET /read_ip_file/`: Read IP addresses from file (JSON response)

## Security Considerations

- Default credentials are hardcoded for demo purposes (admin/admin@123)
- In production, configure proper authentication and credential management
- Ensure the backup directory has appropriate permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the Apache License 2.0.

## Support

For issues and questions:
- Create an issue on GitHub
- Check the NetBox documentation for plugin development guidelines