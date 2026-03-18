from netbox.tables import NetBoxTable
from netbox.tables.columns import ToggleColumn

from netbox_device_type_importer.models import MetaDeviceType

__all__ = ("MetaDeviceTypeTable",)


class MetaDeviceTypeTable(NetBoxTable):
    pk = ToggleColumn(visible=True)
    id = None

    def render_name(self, value):
        return "{}".format(value.split(".")[0])

    class Meta(NetBoxTable.Meta):
        model = MetaDeviceType
        fields = ("pk", "name", "vendor", "is_new", "is_imported")
        default_columns = ("pk", "name", "vendor", "is_imported")
