from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from enginedj.base.models import M_model_base


class M_purchase_request_line(M_model_base, models.Model):
    """Producto y cantidad a comprar. ``order_line_id`` (opcional): la línea de pedido que la motivó
    (``purchase_odoo`` de ``order_dtd_line`` en el .mwb)."""

    model_name = "purchase_request_line"

    purchase_request_id = models.ForeignKey("stock.M_purchase_request", on_delete=models.CASCADE, null=False,
                                            blank=False, related_name="purchase_request_line_purchase_request_id",
                                            db_column="purchase_request_id")
    item_id = models.ForeignKey("orders.M_item", on_delete=models.PROTECT, null=False, blank=False,
                                related_name="purchase_request_line_item_id", db_column="item_id")
    qty = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False,
                              validators=[MinValueValidator(Decimal("0.01"))])
    order_line_id = models.ForeignKey("orders.M_order_line", on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="purchase_request_line_order_line_id", db_column="order_line_id")

    def __str__(self):
        return f"{self.purchase_request_id} · {self.item_id} x {self.qty}"

    class Meta:
        db_table = "purchase_request_line"
        ordering = ["purchase_request_id", "id"]
