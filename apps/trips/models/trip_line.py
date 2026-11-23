from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from enginedj.base.models import M_model_base


class M_trip_line(M_model_base, models.Model):
    """Parada del viaje: una entrega a un destinatario en una dirección."""

    model_name = "trip_line"

    state_choices = [
        ("pending", "Por despachar"),
        ("in_route", "En camino"),
        ("delivering", "En reparto"),
        ("delivered", "Entregado"),
        ("returned", "Devuelto"),
    ]

    trip_id = models.ForeignKey("trips.M_trip", on_delete=models.CASCADE, null=False, blank=False,
                                related_name="trip_line_trip_id", db_column="trip_id")
    sequence = models.PositiveSmallIntegerField(null=False, blank=False, default=1, help_text="ord del .mwb.")
    recipient_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                     related_name="trip_line_recipient_id", db_column="recipient_id",
                                     help_text="company_id_to del .mwb.")
    address_id = models.ForeignKey("locations.M_address", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="trip_line_address_id", db_column="address_id")
    estimated_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False, default=0)
    weight_kg = models.DecimalField(max_digits=12, decimal_places=3, null=False, blank=False, default=0)
    state = models.CharField(max_length=15, null=False, blank=False, choices=state_choices, default="pending",
                             db_index=True)
    is_return = models.BooleanField(default=False, help_text="Hubo devolución en esta parada.")
    return_reason = models.TextField(null=False, blank=True, default="")
    rating = models.PositiveSmallIntegerField(null=True, blank=True,
                                              validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return f"{self.trip_id} · parada {self.sequence}"

    class Meta:
        db_table = "trip_line"
        ordering = ["trip_id", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["trip_id", "sequence"], name="uq_trip_line_sequence"),
        ]
