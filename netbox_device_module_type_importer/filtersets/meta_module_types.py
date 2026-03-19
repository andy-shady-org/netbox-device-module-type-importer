import django_filters

from django.db.models import Q
from utilities.filtersets import register_filterset
from netbox.filtersets import NetBoxModelFilterSet
from netbox_device_module_type_importer.models import MetaModuleType

__all__ = ("MetaModuleTypeFilterSet",)


@register_filterset
class MetaModuleTypeFilterSet(NetBoxModelFilterSet):
    name = django_filters.CharFilter(
        method="by_model",
        label="Model",
    )

    vendor = django_filters.CharFilter(
        method="by_vendor",
        label="Vendor",
    )

    class Meta:
        model = MetaModuleType
        fields = ["name", "vendor"]

    def by_model(self, queryset, name, value):
        if not value.strip():
            return queryset

        return queryset.filter(Q(name__icontains=value))

    def by_vendor(self, queryset, name, value):
        if not value.strip():
            return queryset
        if "," in value:
            q = Q()
            for _ in value.split(","):
                if _:
                    q |= Q(vendor__icontains=_)
            return queryset.filter(q)
        return queryset.filter(Q(vendor__icontains=value))

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        qs_filter = Q(name__icontains=value) | Q(vendor__icontains=value)
        return queryset.filter(qs_filter)
