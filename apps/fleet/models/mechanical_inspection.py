from django.db import models

from enginedj.base.models import M_model_base
from apps.companies.uploads import PrivateUpload


class M_mechanical_inspection(M_model_base, models.Model):
    """Revisión técnico-mecánica."""

    model_name = "mechanical_inspection"

    vehicle_id = models.ForeignKey("fleet.M_vehicle", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="mechanical_inspection_vehicle_id", db_column="vehicle_id")
    certificate_number = models.CharField(max_length=60, null=False, blank=False, help_text="n_certificate del .mwb.")
    cda_name = models.CharField(max_length=150, null=False, blank=False,
                                help_text="name_cda del .mwb: centro de diagnóstico automotor.")
    date_expedition = models.DateField(null=False, blank=False)
    date_expire = models.DateField(null=False, blank=False, db_index=True)
    file = models.FileField(upload_to=PrivateUpload("fleet/rtm"), null=True, blank=True)

    def __str__(self):
        return f"RTM {self.certificate_number} - {self.vehicle_id}"

    class Meta:
        db_table = "mechanical_inspection"
        ordering = ["-date_expire"]
