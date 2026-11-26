from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from enginedj.base.models import M_model_base


class M_order_line(M_model_base, models.Model):
    """``order_dtd_line`` del .mwb: producto, cantidad y destino.

    qty_assigned / qty_delivered los recalcula el sistema desde las
    asignaciones a viajes; qty_pending (qty_available del .mwb) es lo que
    falta por asignar.
    """

    model_name = "order_line"

    state_choices = [
        ("pending", "Pendiente"),
        ("partial", "Parcialmente asignado"),
        ("assigned", "Asignado a viaje"),
        ("delivered", "Entregado"),
        ("cancelled", "Cancelado"),
    ]

    order_id = models.ForeignKey("orders.M_order", on_delete=models.CASCADE, null=False, blank=False,
                                 related_name="order_line_order_id", db_column="order_id")
    item_id = models.ForeignKey("orders.M_item", on_delete=models.PROTECT, null=False, blank=False,
                                related_name="order_line_item_id", db_column="item_id")
    recipient_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                     related_name="order_line_recipient_id", db_column="recipient_id",
                                     help_text="Empresa que pide (dueña de la dirección de entrega); lo pone el sistema.")
    address_id = models.ForeignKey("locations.M_address", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="order_line_address_id", db_column="address_id",
                                   help_text="Dirección de entrega.")
    qty = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False,
                              validators=[MinValueValidator(Decimal("0.01"))])
    qty_assigned = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False, default=0,
                                       editable=False)
    qty_delivered = models.DecimalField(max_digits=12, decimal_places=2, null=False, blank=False, default=0,
                                        editable=False, help_text="qty_delivery del .mwb.")
    state = models.CharField(max_length=15, null=False, blank=False, choices=state_choices, default="pending")

    @property
    def qty_pending(self):
        return self.qty - self.qty_assigned

    def __str__(self):
        return f"{self.order_id} · {self.item_id} x {self.qty}"

    class Meta:
        db_table = "order_line"
        constraints = [
            models.UniqueConstraint(fields=["order_id", "item_id", "address_id"], name="uq_order_line_item_address"),
            models.CheckConstraint(condition=models.Q(qty_assigned__lte=models.F("qty")), name="ck_order_line_assigned"),
            models.CheckConstraint(condition=models.Q(qty_delivered__lte=models.F("qty")), name="ck_order_line_delivered"),
        ]
