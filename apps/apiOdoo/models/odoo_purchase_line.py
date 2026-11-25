from decimal import Decimal

from django.db import models

from enginedj.base.models import M_model_base


class M_odoo_purchase_line(M_model_base, models.Model):
    """Copia local de una línea (purchase.order.line) de una compra de Odoo.

    ``qty_stocked`` es lo que ya sumó al stock de la empresa (app stock): al volver a
    sincronizar solo se suma la diferencia con ``product_qty``.
    """

    model_name = "odoo_purchase_line"

    purchase_id = models.ForeignKey("apiOdoo.M_odoo_purchase", on_delete=models.CASCADE, null=False, blank=False,
                                    related_name="odoo_purchase_line_purchase_id", db_column="purchase_id")
    odoo_line_id = models.PositiveIntegerField(null=False, blank=False, unique=True)
    product_odoo_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    product_name = models.CharField(max_length=255, null=False, blank=True, default="")
    item_id = models.ForeignKey("orders.M_item", on_delete=models.PROTECT, null=True, blank=True,
                                related_name="odoo_purchase_line_item_id", db_column="item_id",
                                help_text="Producto de Hurgo Track (por item.odoo_ref). Vacío = sin emparejar.")
    product_qty = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False, default=Decimal("0"),
                                      help_text="Cantidad comprada.")
    qty_received = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False, default=Decimal("0"))
    uom_name = models.CharField(max_length=60, null=False, blank=True, default="")
    qty_stocked = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False, default=Decimal("0"),
                                      editable=False, help_text="Cantidad que ya entró al stock.")
    raw = models.JSONField(null=False, blank=True, default=dict)

    def __str__(self):
        return f"{self.purchase_id} · {self.product_name} x {self.product_qty}"

    class Meta:
        db_table = "odoo_purchase_line"
        ordering = ["purchase_id", "odoo_line_id"]
