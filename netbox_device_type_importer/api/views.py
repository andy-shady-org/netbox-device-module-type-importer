from rest_framework.routers import APIRootView
from netbox.api.viewsets import NetBoxModelViewSet
from netbox_device_type_importer.models import MetaDeviceType, MetaModuleType
from netbox_device_type_importer.filtersets import (
    MetaDeviceTypeFilterSet,
    MetaModuleTypeFilterSet,
)
from netbox_device_type_importer.api.serializers import (
    MetaDeviceTypeSerializer,
    MetaModuleTypeSerializer,
)


class NetBoxDeviceTypeImporterRootView(APIRootView):
    def get_view_name(self):
        return "NetBoxDeviceTypeImporter"


class MetaDeviceTypeViewSet(NetBoxModelViewSet):
    queryset = MetaDeviceType.objects.all()
    serializer_class = MetaDeviceTypeSerializer
    filterset_class = MetaDeviceTypeFilterSet


class MetaModuleTypeViewSet(NetBoxModelViewSet):
    queryset = MetaModuleType.objects.all()
    serializer_class = MetaModuleTypeSerializer
    filterset_class = MetaModuleTypeFilterSet
