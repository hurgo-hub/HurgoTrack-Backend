from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models.model_base import M_audit_base


class M_order_line_trip(M_audit_base, models.Model):
    """``order_dtd_detail`` del .mwb: parte de una línea de pedido que va en una parada de un viaje."""

    model_name = "order_line_trip"

    order_line_id = models.ForeignKey("orders.M_order_line", on_delete=models.PROTECT, null=False, blank=False,
                                      related_name="order_line_trip_order_line_id", db_column="order_line_id")
    trip_line_id = models.ForeignKey("trips.M_trip_line", on_delete=models.CASCADE, null=False, blank=False,
                                     related_name="order_line_trip_trip_line_id", db_column="trip_line_id")
    qty = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False,
                              validators=[MinValueValidator(Decimal("0.01"))])

    def __str__(self):
        return f"{self.order_line_id} -> {self.trip_line_id} ({self.qty})"

    class Meta:
        db_table = "order_line_trip"
        constraints = [
            models.UniqueConstraint(fields=["order_line_id", "trip_line_id"], name="uq_order_line_trip"),
        ]
