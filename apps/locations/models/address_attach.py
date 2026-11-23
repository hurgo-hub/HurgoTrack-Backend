from django.db import models

from apps.core.models.model_base import M_audit_base


class M_address_attach(M_audit_base, models.Model):
    model_name = "address_attach"

    address_id = models.ForeignKey("locations.M_address", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="address_attach_address_id", db_column="address_id")
    name = models.CharField(max_length=150, null=False, blank=True, default="")
    file = models.FileField(upload_to="addresses/%Y/%m/", null=False, blank=False)

    def __str__(self):
        return self.name or self.file.name

    class Meta:
        db_table = "address_attach"
