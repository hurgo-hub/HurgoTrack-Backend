from django.db import models

from enginedj.base.models import M_catalog_base, M_model_base


class M_fleet_document_type(M_catalog_base, models.Model):
    """Documento que Hurgo exige a vehículos o conductores (además de SOAT, RTM y licencia)."""

    model_name = "fleet_document_type"

    applies_choices = [("vehicle", "Vehículo"), ("driver", "Conductor")]

    applies_to = models.CharField(max_length=10, null=False, blank=False, choices=applies_choices, default="vehicle")
    is_required = models.BooleanField(default=False, help_text="Sin él (vigente) no se asigna el viaje.")
    has_expiration = models.BooleanField(default=True)

    class Meta(M_catalog_base.Meta):
        db_table = "fleet_document_type"


class M_vehicle_document(M_model_base, models.Model):
    model_name = "vehicle_document"

    vehicle_id = models.ForeignKey("fleet.M_vehicle", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="vehicle_document_vehicle_id", db_column="vehicle_id")
    type_id = models.ForeignKey("fleet.M_fleet_document_type", on_delete=models.PROTECT, null=False, blank=False,
                                related_name="vehicle_document_type_id", db_column="type_id")
    file = models.FileField(upload_to="fleet/documents/%Y/", null=False, blank=False)
    date_expire = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "vehicle_document"
        ordering = ["vehicle_id", "type_id", "-date_expire"]


class M_driver_document(M_model_base, models.Model):
    model_name = "driver_document"

    driver_id = models.ForeignKey("drivers.M_driver", on_delete=models.CASCADE, null=False, blank=False,
                                  related_name="driver_document_driver_id", db_column="driver_id")
    type_id = models.ForeignKey("fleet.M_fleet_document_type", on_delete=models.PROTECT, null=False, blank=False,
                                related_name="driver_document_type_id", db_column="type_id")
    file = models.FileField(upload_to="drivers/documents/%Y/", null=False, blank=False)
    date_expire = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "driver_document"
        ordering = ["driver_id", "type_id", "-date_expire"]
