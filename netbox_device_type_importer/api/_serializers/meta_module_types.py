from rest_framework.serializers import (
    HyperlinkedIdentityField,
)
from netbox.api.serializers import NetBoxModelSerializer

from netbox_device_type_importer.models import MetaModuleType


class MetaModuleTypeSerializer(NetBoxModelSerializer):
    url = HyperlinkedIdentityField(
        view_name="plugins-api:netbox_device_type_importer-api:metamoduletype-detail"
    )

    class Meta:
        model = MetaModuleType
        fields = (
            "id",
            "url",
            "display",
            "name",
            "vendor",
            "sha",
            "download_url",
            "is_new",
            "imported_dt",
            "is_imported",
        )
        brief_fields = (
            "id",
            "url",
            "display",
            "name",
            "vendor",
            "sha",
            "download_url",
            "is_new",
            "imported_dt",
            "is_imported",
        )
