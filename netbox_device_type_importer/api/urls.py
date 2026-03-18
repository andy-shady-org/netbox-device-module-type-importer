from netbox.api.routers import NetBoxRouter

from .views import (
    NetBoxDeviceTypeImporterRootView,
    MetaDeviceTypeViewSet,
    MetaModuleTypeViewSet,
)

app_name = "netbox_device_type_importer"

router = NetBoxRouter()
router.APIRootView = NetBoxDeviceTypeImporterRootView
router.register("meta-device-types", MetaDeviceTypeViewSet)
router.register("meta-module-types", MetaModuleTypeViewSet)
urlpatterns = router.urls
