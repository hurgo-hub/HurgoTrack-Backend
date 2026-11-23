from django.db import models

from enginedj.base.choices import LICENSE_CATEGORY_CHOICES
from enginedj.base.models import M_model_base


class M_vehicle(M_model_base, models.Model):
    model_name = "vehicle"

    fuel_type_choices = [
        ("acpm", "ACPM / Diésel"),
        ("gasoline", "Gasolina"),
        ("gas", "Gas natural"),
        ("electric", "Eléctrico"),
    ]
    transmission_choices = [
        ("manual", "Manual"),
        ("automatic", "Automática"),
    ]

    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="vehicle_company_id", db_column="company_id",
                                   help_text="Transportador dueño de la operación (Hurgo o independiente).")
    plate = models.CharField(max_length=10, null=False, blank=False, unique=True)
    brand_vehicle_id = models.ForeignKey("fleet.M_brand_vehicle", on_delete=models.PROTECT, null=False, blank=False,
                                         related_name="vehicle_brand_vehicle_id", db_column="brand_vehicle_id")
    type_vehicle_id = models.ForeignKey("fleet.M_type_vehicle", on_delete=models.PROTECT, null=False, blank=False,
                                        related_name="vehicle_type_vehicle_id", db_column="type_vehicle_id")
    bodywork_id = models.ForeignKey("fleet.M_bodywork", on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="vehicle_bodywork_id", db_column="bodywork_id")
    transit_id = models.ForeignKey("fleet.M_transit", on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="vehicle_transit_id", db_column="transit_id")
    model_year = models.PositiveSmallIntegerField(null=True, blank=True, help_text="model del .mwb: modelo (año).")
    color = models.CharField(max_length=60, null=False, blank=True, default="")
    load_capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    empty_weight_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                          help_text="weight del .mwb.")
    motorcycle_capacity = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Cuántas motos carga.")
    vin = models.CharField(max_length=30, null=False, blank=True, default="")
    fuel_type = models.CharField(max_length=10, null=False, blank=True, default="", choices=fuel_type_choices)
    license_category = models.CharField(max_length=2, null=False, blank=True, default="",
                                        choices=LICENSE_CATEGORY_CHOICES,
                                        help_text="clasification del .mwb: categoría de licencia que exige.")
    transmission = models.CharField(max_length=10, null=False, blank=True, default="", choices=transmission_choices,
                                    help_text="type_engine del .mwb.")
    plate_transit_free = models.BooleanField(default=False)
    owner_id = models.ForeignKey("fleet.M_partner", on_delete=models.PROTECT, null=False, blank=False,
                                 related_name="vehicle_owner_id", db_column="owner_id", help_text="Propietario.")
    holder_id = models.ForeignKey("fleet.M_partner", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="vehicle_holder_id", db_column="holder_id",
                                  help_text="other_owner_id del .mwb: tenedor, si es distinto del propietario.")
    default_driver_id = models.ForeignKey("drivers.M_driver", on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name="vehicle_default_driver_id", db_column="default_driver_id",
                                          help_text="drive_id del .mwb: conductor habitual. El de cada viaje va en el viaje.")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.plate

    class Meta:
        db_table = "vehicle"
        ordering = ["plate"]
