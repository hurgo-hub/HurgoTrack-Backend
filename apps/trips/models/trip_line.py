from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from enginedj.base.models import M_model_base


class M_trip_line(M_model_base, models.Model):
    """Parada del viaje: una entrega a una dirección de la empresa que pide.

    La dirección vive en el esquema de la empresa; aquí (central) queda una copia de lo que
    necesita el conductor y el mapa, y ``address_ref`` = id de la dirección en ese esquema.
    """

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
    address_ref = models.PositiveIntegerField(null=True, blank=True, db_index=True,
                                              help_text="Id de la dirección de entrega en el esquema de la empresa.")
    address_name = models.CharField(max_length=120, null=False, blank=True, default="")
    address_text = models.CharField(max_length=255, null=False, blank=True, default="")
    location_name = models.CharField(max_length=160, null=False, blank=True, default="", help_text="Municipio.")
    address_description = models.TextField(null=False, blank=True, default="")
    contact_name = models.CharField(max_length=150, null=False, blank=True, default="")
    contact_phone = models.CharField(max_length=40, null=False, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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

    def copy_address(self, address):
        """Copia la dirección (de la empresa o un lugar de cargue) en la parada."""
        self.address_ref = address.pk
        self.address_name = address.name
        self.address_text = address.address
        self.location_name = address.location_id.name if address.location_id_id else ""
        self.address_description = getattr(address, "description", "") or ""
        self.contact_name = getattr(address, "contact_name", "") or ""
        self.contact_phone = getattr(address, "contact_phone", "") or ""
        self.latitude = getattr(address, "latitude", None)
        self.longitude = getattr(address, "longitude", None)
