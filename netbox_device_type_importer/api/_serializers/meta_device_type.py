from rest_framework.serializers import (
    HyperlinkedIdentityField,
)
from netbox.api.serializers import NetBoxModelSerializer

from netbox_device_type_importer.models import MetaDeviceType


class MetaDeviceTypeSerializer(NetBoxModelSerializer):
    url = HyperlinkedIdentityField(
        view_name="plugins-api:netbox_device_type_importer-api:metadevicetype-detail"
    )

    class Meta:
        model = MetaDeviceType
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
