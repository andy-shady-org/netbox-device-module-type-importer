# NetBox Device Type Importer Plugin
[Netbox](https://github.com/netbox-community/netbox) plugin for easy import DeviceType from [NetBox Device Type Library](https://github.com/netbox-community/devicetype-library).

<div align="center">
<a href="https://pypi.org/project/netbox-device-type-importer/"><img src="https://img.shields.io/pypi/v/netbox-device-type-importer" alt="PyPi"/></a>
<a href="https://github.com/andy-shady-org/netbox-device-type-importer/stargazers"><img src="https://img.shields.io/github/stars/andy-shady-org/netbox-device-type-importer?style=flat" alt="Stars Badge"/></a>
<a href="https://github.com/andy-shady-org/netbox-device-type-importer/network/members"><img src="https://img.shields.io/github/forks/andy-shady-org/netbox-device-type-importer?style=flat" alt="Forks Badge"/></a>
<a href="https://github.com/andy-shady-org/netbox-device-type-importer/issues"><img src="https://img.shields.io/github/issues/andy-shady-org/netbox-device-type-importer" alt="Issues Badge"/></a>
<a href="https://github.com/andy-shady-org/netbox-device-type-importer/pulls"><img src="https://img.shields.io/github/issues-pr/andy-shady-org/netbox-device-type-importer" alt="Pull Requests Badge"/></a>
<a href="https://github.com/andy-shady-org/netbox-device-type-importer/graphs/contributors"><img alt="GitHub contributors" src="https://img.shields.io/github/contributors/andy-shady-org/netbox-device-type-importer?color=2b9348"></a>
<a href="https://github.com/andy-shady-org/netbox-device-type-importer/blob/master/LICENSE"><img src="https://img.shields.io/github/license/andy-shady-org/netbox-device-type-importer?color=2b9348" alt="License Badge"/></a>
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style Black"/></a>
<a href="https://pepy.tech/project/netbox-device-type-importer"><img alt="Downloads" src="https://static.pepy.tech/badge/netbox-device-type-importer"></a>
<a href="https://pepy.tech/project/netbox-device-type-importer"><img alt="Downloads/Week" src="https://static.pepy.tech/badge/netbox-device-type-importer/month"></a>
<a href="https://pepy.tech/project/netbox-device-type-importer"><img alt="Downloads/Month" src="https://static.pepy.tech/badge/netbox-device-type-importer/week"></a>
</div>


## Description

The plugin uses [GitHub GraphQL API](https://docs.github.com/en/graphql) to load DeviceType from [NetBox Device Type Library](https://github.com/netbox-community/devicetype-library). The plugin loads only file tree representation from github repo and shows it as a table with vendor and model columns. DeviceType definitions files are loaded when you try to import selected models.
To use GraphQL API you need to set GitHub personal access token in plugin settings.  You don't need to grant any permissions to the token.    
How to create the token, see ["Creating a personal access token."](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token)

## Compatibility

| NetBox Version | NetBox Device Type Importer Version |
|----------------|-------------------------------------|
| NetBox 4.5     | \>= 0.0.1                           |

## Installation

The plugin is available as a Python package in pypi and can be installed with pip  

```
pip install netbox-device-type-importer
```
Enable the plugin in /opt/netbox/netbox/netbox/configuration.py:
```
PLUGINS = ['netbox_device_type_importer',]
```
Restart NetBox and add `netbox-device-type-importer` to your local_requirements.txt

Perform database migrations:
```bash
cd /opt/netbox
source venv/bin/activate
python ./netbox/manage.py migrate netbox_device_type_importer
python ./netbox/manage.py reindex netbox_device_type_importer
```

Full documentation on using plugins with NetBox: [Using Plugins - NetBox Documentation](https://netbox.readthedocs.io/en/stable/plugins/)


## Configuration

Put your GitHub personal access token to [NetBox plugins config](https://netbox.readthedocs.io/en/stable/configuration/optional-settings/#plugins_config)  
```
PLUGINS_CONFIG = {
    'netbox_devicetype_importer': {
        'github_token': '<YOUR-GITHUB-TOKEN>'
    }
}
```

## Contribute

Contributions are always welcome! Please see the [Contribution Guidelines](CONTRIBUTING.md)


## Screenshots

![](docs/img/import.gif) 

## Future 
* Import device images from GitHub repo
* Add a GitHub REST API client that allows this plugin to be used without the GitHub token
* Allow for the import of device types from alternate repositories


## Credits

- Thanks to Nikolay Yuzefovich for providing the original version of this plugin located at https://github.com/nikolay-yuzefovich/netbox-device-type-importer.

