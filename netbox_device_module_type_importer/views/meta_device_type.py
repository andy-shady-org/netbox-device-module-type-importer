from collections import OrderedDict
from urllib.parse import urlencode
import time

from django.conf import settings
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, reverse
from django.utils.text import slugify
from django.views.generic import View
from django.forms import DecimalField, HiddenInput

from netbox.views import generic
from utilities.views import register_model_view
from dcim.models import Manufacturer, DeviceType
from dcim import forms
from utilities.forms import restrict_form_fields
from utilities.forms.bulk_import import BulkImportForm
from utilities.exceptions import AbortTransaction, PermissionsViolation
from utilities.views import ContentTypePermissionRequiredMixin
from netbox.object_actions import BulkDelete

from netbox_device_module_type_importer.models import MetaDeviceType
from netbox_device_module_type_importer.tables import MetaDeviceTypeTable
from netbox_device_module_type_importer.filtersets import MetaDeviceTypeFilterSet
from netbox_device_module_type_importer.forms import MetaDeviceTypeFilterForm
from netbox_device_module_type_importer.utilities import GitHubGQLAPIAsync, GQLError

__all__ = (
    "MetaDeviceTypeListView",
    "MetaDeviceTypeEditView",
    "MetaDeviceTypeImportView",
)


@register_model_view(MetaDeviceType, "list", path="", detail=False)
class MetaDeviceTypeListView(generic.ObjectListView):
    queryset = MetaDeviceType.objects.all()
    filterset = MetaDeviceTypeFilterSet
    filterset_form = MetaDeviceTypeFilterForm
    table = MetaDeviceTypeTable
    action_buttons = ("delete",)
    actions = (BulkDelete,)
    template_name = "netbox_device_module_type_importer/metadevicetype_list.html"


@register_model_view(MetaDeviceType, "delete")
class MetaDeviceTypeDeleteView(generic.ObjectDeleteView):
    queryset = MetaDeviceType.objects.all()


@register_model_view(MetaDeviceType, "bulk_delete", path="delete", detail=False)
class MetaDeviceTypeBulkDeleteView(generic.BulkDeleteView):
    queryset = MetaDeviceType.objects.all()
    table = MetaDeviceTypeTable


@register_model_view(MetaDeviceType, "load", detail=False)
@register_model_view(MetaDeviceType, "edit")
class MetaDeviceTypeEditView(ContentTypePermissionRequiredMixin, View):
    def get_required_permission(self):
        return "netbox_devicetype_importer.add_metadevicetype"

    def post(self, request):
        loaded = 0
        created = 0
        updated = 0
        if not request.user.has_perm(
            "netbox_device_module_type_importer.add_metadevicetype"
        ):
            return HttpResponseForbidden()
        plugin_settings = settings.PLUGINS_CONFIG.get(
            "netbox_device_module_type_importer", {}
        )
        token = plugin_settings.get("github_token")
        repo = plugin_settings.get("repo")
        owner = plugin_settings.get("repo_owner")
        url = plugin_settings.get("github_url")
        batch_size = plugin_settings.get("batch_size", 50)
        max_concurrent_requests = plugin_settings.get("max_concurrent_requests", 10)
        max_concurrent_vendors = plugin_settings.get("max_concurrent_vendors", 5)

        if token:
            gh_api = GitHubGQLAPIAsync(url=url, token=token, owner=owner, repo=repo)
        else:
            messages.error(request, message=f"No Github Token Found")
            return redirect(
                "plugins:netbox_device_module_type_importer:metadevicetype_list"
            )
        try:
            models = gh_api.get_tree(
                batch_size=batch_size,
                max_concurrent_requests=max_concurrent_requests,
                max_concurrent_vendors=max_concurrent_vendors,
            )
        except GQLError as e:
            messages.error(request, message=f"GraphQL API Error: {e.message}")
            return redirect(
                "plugins:netbox_device_module_type_importer:metadevicetype_list"
            )

        existing_records = {
            (record.vendor, record.name): record
            for record in MetaDeviceType.objects.all()
        }

        for vendor, vendor_models in models.items():
            for model, model_data in vendor_models.items():
                loaded += 1
                key = (vendor, model)

                if key in existing_records:
                    existing_record = existing_records[key]
                    sha_changed = existing_record.sha != model_data["sha"]

                    if sha_changed:
                        existing_record.sha = model_data["sha"]
                        existing_record.is_new = True
                        updated += 1
                    else:
                        existing_record.is_new = False

                    existing_record.save()
                else:
                    new_record = MetaDeviceType(
                        vendor=vendor, name=model, sha=model_data["sha"], is_new=True
                    )
                    new_record.save()
                    created += 1

        messages.success(
            request, f"Loaded: {loaded}, Created: {created}, Updated: {updated}"
        )
        return redirect(
            "plugins:netbox_device_module_type_importer:metadevicetype_list"
        )


@register_model_view(MetaDeviceType, "bulk_import", detail=False)
class MetaDeviceTypeImportView(ContentTypePermissionRequiredMixin, View):
    queryset = MetaDeviceType.objects.all()
    filterset = MetaDeviceTypeFilterSet
    filterset_form = MetaDeviceTypeFilterForm

    related_object_forms = OrderedDict(
        (
            ("console-ports", forms.ConsolePortTemplateImportForm),
            ("console-server-ports", forms.ConsoleServerPortTemplateImportForm),
            ("power-ports", forms.PowerPortTemplateImportForm),
            ("power-outlets", forms.PowerOutletTemplateImportForm),
            ("interfaces", forms.InterfaceTemplateImportForm),
            ("rear-ports", forms.RearPortTemplateImportForm),
            ("front-ports", forms.FrontPortTemplateImportForm),
            ("device-bays", forms.DeviceBayTemplateImportForm),
        )
    )

    def get_required_permission(self):
        return "netbox_device_module_type_importer.add_metadevicetype"

    def post(self, request):
        vendor_count = 0
        errored = 0
        imported_dt = []
        model = self.queryset.model

        if request.POST.get("_all"):
            if self.filterset is not None:
                pk_list = [
                    obj.pk
                    for obj in self.filterset(request.GET, model.objects.only("pk")).qs
                ]
            else:
                pk_list = model.objects.values_list("pk", flat=True)
        else:
            pk_list = [int(pk) for pk in request.POST.getlist("pk")]

        plugin_settings = settings.PLUGINS_CONFIG.get(
            "netbox_device_module_type_importer", {}
        )
        token = plugin_settings.get("github_token")
        repo = plugin_settings.get("repo")
        owner = plugin_settings.get("repo_owner")
        url = plugin_settings.get("github_url")
        version_minor = settings.VERSION.split(".")[1]

        # for 3.2 new device type components
        if int(version_minor) >= 2:
            self.related_object_forms.popitem()
            self.related_object_forms.update(
                {
                    "module-bays": forms.ModuleBayTemplateImportForm,
                    "device-bays": forms.DeviceBayTemplateImportForm,
                    "inventory-items": forms.InventoryItemTemplateImportForm,
                }
            )

        if token:
            gh_api = GitHubGQLAPIAsync(url=url, token=token, owner=owner, repo=repo)
        else:
            messages.error(request, message=f"No Github Token Found")
            return redirect(
                "plugins:netbox_device_module_type_importer:metadevicetype_list"
            )

        query_data = {}
        # check already imported mdt
        already_imported_mdt = model.objects.filter(pk__in=pk_list, is_imported=True)
        if already_imported_mdt.exists():
            for _mdt in already_imported_mdt:
                if DeviceType.objects.filter(pk=_mdt.imported_dt).exists() is False:
                    _mdt.imported_dt = None
                    _mdt.save()
        vendors_for_cre = set(
            model.objects.filter(pk__in=pk_list).values_list("vendor", flat=True)
        )
        for vendor, name, sha in model.objects.filter(
            pk__in=pk_list, is_imported=False
        ).values_list("vendor", "name", "sha"):
            query_data[sha] = f"{vendor}/{name}"
        if not query_data:
            messages.warning(request, message="Nothing to import")
            return redirect(
                "plugins:netbox_device_module_type_importer:metadevicetype_list"
            )
        try:
            dt_files = gh_api.get_files(query_data)
        except GQLError as e:
            dt_files = {}
            messages.error(request, message=f"GraphQL API Error: {e.message}")
            return redirect(
                "plugins:netbox_device_module_type_importer:metadevicetype_list"
            )
        # cre manufacturers
        for vendor in vendors_for_cre:
            manu, _ = Manufacturer.objects.get_or_create(
                name=vendor, slug=slugify(vendor)
            )
            if _:
                vendor_count += 1

        for sha, yaml_text in dt_files.items():
            form = BulkImportForm(data={"data": yaml_text, "format": "yaml"})
            if form.is_valid():
                data = form.cleaned_data["data"][0]
                data["_init_time"] = 1
                model_form = forms.DeviceTypeImportForm(data)
                # is it necessary?
                restrict_form_fields(model_form, request.user)

                for field_name, field in model_form.fields.items():
                    if field_name not in data and hasattr(field, "initial"):
                        try:
                            model_form.data[field_name] = field.initial
                        except Exception:
                            messages.error(
                                request,
                                message=f"{type(model_form.data)} - {model_form.data} - {str(field)}",
                            )
                            return redirect(
                                "plugins:netbox_device_type_importer:metadevicetype_list"
                            )

                if model_form.is_valid():
                    try:
                        with transaction.atomic():
                            obj = model_form.save()

                            for (
                                field_name,
                                related_object_form,
                            ) in self.related_object_forms.items():
                                related_obj_pks = []
                                for i, rel_obj_data in enumerate(
                                    data.get(field_name, list())
                                ):
                                    if int(version_minor) >= 2:
                                        rel_obj_data.update({"device_type": obj})
                                        f = related_object_form(rel_obj_data)
                                    else:
                                        f = related_object_form(obj, rel_obj_data)
                                    for subfield_name, field in f.fields.items():
                                        if (
                                            subfield_name not in rel_obj_data
                                            and hasattr(field, "initial")
                                        ):
                                            f.data[subfield_name] = field.initial
                                    if f.is_valid():
                                        related_obj = f.save()
                                        related_obj_pks.append(related_obj.pk)
                                    else:
                                        for subfield_name, errors in f.errors.items():
                                            for err in errors:
                                                err_msg = "{}[{}] {}: {}".format(
                                                    field_name, i, subfield_name, err
                                                )
                                                model_form.add_error(None, err_msg)
                                        raise AbortTransaction()
                    except AbortTransaction as e:
                        messages.error(
                            request,
                            f"Failed to import Device Type, exception raised: {str(e)}",
                        )
                        pass
                    except PermissionsViolation:
                        errored += 1
                        continue
                if model_form.errors:
                    errored += 1
                    messages.error(
                        request,
                        f"Failed to import Device Type, form has errors: {model_form.errors}",
                    )
                else:
                    imported_dt.append(obj.pk)
                    metadt = MetaDeviceType.objects.get(sha=sha)
                    metadt.imported_dt = obj.pk
                    metadt.save()
            else:
                errored += 1
                messages.error(
                    request, f"Failed to import Device Type, form not valid: {obj.name}"
                )
        # msg
        if imported_dt:
            messages.success(request, f"Imported: {imported_dt.__len__()}")
            if errored:
                messages.error(request, f"Failed: {errored}")
            qparams = urlencode({"id": imported_dt}, doseq=True)
            return redirect(reverse("dcim:devicetype_list") + "?" + qparams)
        else:
            messages.error(request, f"Can not import Device Types")
            return redirect("plugins:netbox_device_type_importer:metadevicetype_list")
