from django.db import models

from apps.core.fields import EncryptedTextField
from apps.core.models.model_base import M_audit_base


class M_vehicle_gps(M_audit_base, models.Model):
    """gps_operator / gps_user / gps_password / gps_apikey / gps_secret del .mwb, separados y cifrados (fase 4)."""

    model_name = "vehicle_gps"

    vehicle_id = models.OneToOneField("fleet.M_vehicle", on_delete=models.CASCADE, null=False, blank=False,
                                      related_name="vehicle_gps_vehicle_id", db_column="vehicle_id")
    operator = models.CharField(max_length=120, null=False, blank=False)
    username = models.CharField(max_length=120, null=False, blank=True, default="")
    password = EncryptedTextField(null=False, blank=True, default="")
    api_key = EncryptedTextField(null=False, blank=True, default="")
    api_secret = EncryptedTextField(null=False, blank=True, default="")

    def __str__(self):
        return f"GPS {self.vehicle_id} ({self.operator})"

    class Meta:
        db_table = "vehicle_gps"
