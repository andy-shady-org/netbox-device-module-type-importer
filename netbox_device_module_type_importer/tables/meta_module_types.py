from netbox.tables import NetBoxTable
from netbox.tables.columns import ToggleColumn, BooleanColumn

from netbox_device_module_type_importer.models import MetaModuleType

__all__ = ("MetaModuleTypeTable",)


class MetaModuleTypeTable(NetBoxTable):
    pk = ToggleColumn(visible=True)
    id = None
    is_new = BooleanColumn()
    is_imported = BooleanColumn()

    def render_name(self, value):
        return "{}".format(value.split(".")[0])

    class Meta(NetBoxTable.Meta):
        model = MetaModuleType
        fields = ("pk", "name", "vendor", "is_new", "is_imported")
        default_columns = ("pk", "name", "vendor", "is_imported")
