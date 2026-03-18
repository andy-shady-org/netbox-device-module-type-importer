from django import forms

from netbox.forms import (
    NetBoxModelFilterSetForm,
)

from netbox_device_type_importer.models import MetaDeviceType

__all__ = ("MetaDeviceTypeFilterForm",)


class MetaDeviceTypeFilterForm(NetBoxModelFilterSetForm):
    model = MetaDeviceType
    name = forms.CharField(required=False, label="Model")
    vendor = forms.CharField(required=False, label="Vendor")
