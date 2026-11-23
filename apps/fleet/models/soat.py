from django.db import models

from enginedj.base.models import M_model_base


class M_soat(M_model_base, models.Model):
    model_name = "soat"

    vehicle_id = models.ForeignKey("fleet.M_vehicle", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="soat_vehicle_id", db_column="vehicle_id")
    insurer_name = models.CharField(max_length=150, null=False, blank=False, help_text="insurance_name del .mwb.")
    policy_number = models.CharField(max_length=60, null=False, blank=False, help_text="policy del .mwb.")
    date_start = models.DateField(null=True, blank=True)
    date_expire = models.DateField(null=False, blank=False, db_index=True)
    file = models.FileField(upload_to="fleet/soat/%Y/", null=True, blank=True)

    def __str__(self):
        return f"SOAT {self.policy_number} - {self.vehicle_id}"

    class Meta:
        db_table = "soat"
        ordering = ["-date_expire"]
