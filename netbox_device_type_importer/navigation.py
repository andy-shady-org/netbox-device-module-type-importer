from django.utils.translation import gettext_lazy as _
from netbox.plugins import PluginMenuItem

menu_items = (
    PluginMenuItem(
        link="plugins:netbox_device_type_importer:metadevicetype_list",
        link_text=_("Device Type Import"),
        permissions=["netbox_device_type_importer.view_metadevicetype"],
        buttons=(),
    ),
    PluginMenuItem(
        link="plugins:netbox_device_type_importer:metamoduletype_list",
        link_text=_("Module Type Import"),
        permissions=["netbox_device_type_importer.view_metamoduletype"],
        buttons=(),
    ),
)
