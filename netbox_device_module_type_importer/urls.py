from django.urls import include, path
from utilities.urls import get_model_urls

# +
# Import views so the register_model_view is run. This is required for the
# URLs to be set up properly with get_model_urls().
# -
from .views import *  # noqa: F401

app_name = "netbox_device_module_type_importer"

urlpatterns = [
    path(
        "meta-device-types/",
        include(
            get_model_urls(
                "netbox_device_module_type_importer", "metadevicetype", detail=False
            )
        ),
    ),
    path(
        "meta-device-types/<int:pk>/",
        include(get_model_urls("netbox_device_module_type_importer", "metadevicetype")),
    ),
    path(
        "meta-module-types/",
        include(
            get_model_urls(
                "netbox_device_module_type_importer", "metamoduletype", detail=False
            )
        ),
    ),
    path(
        "meta-module-types/<int:pk>/",
        include(get_model_urls("netbox_device_module_type_importer", "metamoduletype")),
    ),
]
