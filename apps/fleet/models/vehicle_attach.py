from django.db import models

from enginedj.base.models import M_model_base
from apps.companies.uploads import PrivateUpload


class M_vehicle_attach(M_model_base, models.Model):
    model_name = "vehicle_attach"

    vehicle_id = models.ForeignKey("fleet.M_vehicle", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="vehicle_attach_vehicle_id", db_column="vehicle_id")
    name = models.CharField(max_length=150, null=False, blank=False, help_text="Ej. tarjeta de propiedad, póliza.")
    file = models.FileField(upload_to=PrivateUpload("fleet/attachments"), null=False, blank=False)
    date_expire = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "vehicle_attach"
