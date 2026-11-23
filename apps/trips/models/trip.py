from django.db import models

from enginedj.base.models import M_model_base


class M_trip(M_model_base, models.Model):
    """Viaje: el corazón del sistema.

    ``company_id`` (company_id_do del .mwb): empresa cliente dueña de la carga.
    El destinatario de cada entrega (company_id_to) va en cada parada.
    """

    model_name = "trip"
    letter = "V"  # código V-XXXXXX que genera M_model_base

    trip_type_choices = [
        ("delivery", "Entrega"),
        ("return", "Devolución"),
    ]
    state_choices = [
        ("draft", "Armando"),
        ("assigned", "Vehículo y conductor asignados"),
        ("in_route", "En camino"),
        ("delivering", "En reparto"),
        ("closed", "Cerrado"),
        ("cancelled", "Cancelado"),
    ]

    code = models.CharField(max_length=20, null=False, blank=False, unique=True, editable=False)
    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="trip_company_id", db_column="company_id")
    trip_type = models.CharField(max_length=10, null=False, blank=False, choices=trip_type_choices, default="delivery")
    state = models.CharField(max_length=15, null=False, blank=False, choices=state_choices, default="draft",
                             db_index=True)
    brand_id = models.ForeignKey("orders.M_brand", on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="trip_brand_id", db_column="brand_id",
                                 help_text="Marca única del viaje cuando lleva motos.")
    carrier_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="trip_carrier_id", db_column="carrier_id",
                                   help_text="Transportador que hace el viaje.")
    vehicle_id = models.ForeignKey("fleet.M_vehicle", on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="trip_vehicle_id", db_column="vehicle_id")
    driver_id = models.ForeignKey("drivers.M_driver", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="trip_driver_id", db_column="driver_id")
    origin_address_id = models.ForeignKey("locations.M_address", on_delete=models.PROTECT, null=False, blank=False,
                                          related_name="trip_origin_address_id", db_column="origin_address_id",
                                          help_text="address_id del .mwb: bodega de cargue.")
    parent_trip_id = models.ForeignKey("trips.M_trip", on_delete=models.PROTECT, null=True, blank=True,
                                       related_name="trip_parent_trip_id", db_column="parent_trip_id",
                                       help_text="trip_id del .mwb: viaje original de un viaje de regreso.")
    returned_line_id = models.ForeignKey("trips.M_trip_line", on_delete=models.PROTECT, null=True, blank=True,
                                         related_name="trip_returned_line_id", db_column="returned_line_id",
                                         help_text="Parada devuelta que originó este viaje de regreso.")
    planned_departure = models.DateTimeField(null=True, blank=True)
    departure_date = models.DateTimeField(null=True, blank=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return self.code

    class Meta:
        db_table = "trip"
        ordering = ["-id"]
        permissions = [
            ("build_trip", "Puede armar viajes"),
            ("register_series_trip", "Puede registrar motos por VIN"),
            ("assign_trip", "Puede asignar vehículo y conductor"),
            ("cancel_trip", "Puede cancelar viajes"),
            ("create_return_trip", "Puede generar viajes de regreso"),
            ("drive_trip", "Puede operar viajes como conductor (salida, reparto, entrega, devolución)"),
            ("report_novelty_trip", "Puede reportar novedades"),
            ("view_all_trip", "Puede ver todos los viajes"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(state__in=["assigned", "in_route", "delivering", "closed"])
                | (models.Q(vehicle_id__isnull=False) & models.Q(driver_id__isnull=False)),
                name="ck_trip_assigned_has_vehicle_driver",
            ),
        ]
