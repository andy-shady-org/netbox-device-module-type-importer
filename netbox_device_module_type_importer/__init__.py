from django.utils.translation import gettext_lazy as _
from netbox.plugins import PluginConfig
from .version import __version__


class DeviceTypeImporterConfig(PluginConfig):
    name = "netbox_device_module_type_importer"
    verbose_name = _("Device and Module Type Importer")
    description = _("Import Device and Module Types from a Github repo")
    version = __version__
    author = "Andy Wilson"
    author_email = "andy@shady.org"
    base_url = "netbox-device-module-type-importer"
    required_settings = []
    min_version = "4.5.0"
    default_settings = {
        "repo_owner": "netbox-community",
        "repo": "devicetype-library",
        "github_token": "",
        "github_url": "https://api.github.com/graphql",
        "batch_size": 50,
        "max_concurrent_requests": 20,
        "max_concurrent_vendors": 20,
    }


config = DeviceTypeImporterConfig  # noqa
