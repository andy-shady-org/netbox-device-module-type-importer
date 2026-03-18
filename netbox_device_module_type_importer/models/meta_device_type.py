from django.urls import reverse
from django.db import models
from django.utils.translation import gettext_lazy as _

from netbox.models import NetBoxModel
from utilities.querysets import RestrictedQuerySet

__all__ = ("MetaDeviceType",)


class MetaDeviceType(NetBoxModel):
    name = models.CharField(max_length=100)
    vendor = models.CharField(max_length=50)
    sha = models.CharField(max_length=40)
    download_url = models.URLField(null=True, blank=True)
    is_new = models.BooleanField(default=True)
    imported_dt = models.IntegerField(null=True, blank=True)
    is_imported = models.BooleanField(default=False)

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        verbose_name_plural = _("Meta Device Types")
        ordering = ("name", "vendor", "download_url")

    def __str__(self):
        return self.name.split(".")[0]

    def get_absolute_url(self):
        return reverse(
            "plugins:netbox_device_module_type_importer:metadevicetype", args=[self.pk]
        )

    def save(self, *args, **kwargs):
        if self.imported_dt:
            self.is_imported = True
            self.is_new = False
        else:
            self.is_imported = False
        super(MetaDeviceType, self).save(*args, **kwargs)
