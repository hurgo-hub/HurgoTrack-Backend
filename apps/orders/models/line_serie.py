from django.db import models

from enginedj.base.models import M_model_base


class M_trip_line_serie(M_model_base, models.Model):
    """Una moto (unidad serializada) de una parada, identificada por su VIN.

    Vive en el esquema de la empresa (sus productos); apunta a la parada central del viaje.
    """

    model_name = "trip_line_serie"

    state_choices = [
        ("pending", "Por entregar"),
        ("delivered", "Entregado"),
        ("returned", "Devuelto"),
    ]

    trip_line_id = models.ForeignKey("trips.M_trip_line", on_delete=models.CASCADE, null=False, blank=False,
                                     related_name="trip_line_serie_trip_line_id", db_column="trip_line_id")
    order_line_trip_id = models.ForeignKey("orders.M_order_line_trip", on_delete=models.PROTECT, null=True, blank=True,
                                           related_name="trip_line_serie_order_line_trip_id",
                                           db_column="order_line_trip_id",
                                           help_text="Línea de pedido de la que sale la unidad (da el producto).")
    vin = models.CharField(max_length=30, null=False, blank=False, db_index=True)
    engine_number = models.CharField(max_length=30, null=False, blank=True, default="")
    state = models.CharField(max_length=10, null=False, blank=False, choices=state_choices, default="pending")

    def __str__(self):
        return self.vin

    class Meta:
        db_table = "trip_line_serie"
        constraints = [
            models.UniqueConstraint(fields=["trip_line_id", "vin"], name="uq_trip_line_serie_vin"),
        ]
