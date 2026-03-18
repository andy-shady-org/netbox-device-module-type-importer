from django import forms

from netbox.forms import (
    NetBoxModelFilterSetForm,
)

from netbox_device_type_importer.models import MetaModuleType

__all__ = ("MetaModuleTypeFilterForm",)


class MetaModuleTypeFilterForm(NetBoxModelFilterSetForm):
    model = MetaModuleType
    name = forms.CharField(required=False, label="Model")
    vendor = forms.CharField(required=False, label="Vendor")
