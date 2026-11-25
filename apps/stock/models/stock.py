from decimal import Decimal

from django.db import models

from enginedj.base.models import M_model_base


class M_stock(M_model_base, models.Model):
    """Stock disponible de una empresa por producto: lo comprado en Odoo que aún no se ha cargado.

    Una fila por empresa + producto (sin bodega). Solo se mueve por ``M_stock_move``.
    """

    model_name = "stock"

    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="stock_company_id", db_column="company_id",
                                   help_text="Empresa dueña del stock (ej. Distritodo).")
    item_id = models.ForeignKey("orders.M_item", on_delete=models.PROTECT, null=False, blank=False,
                                related_name="stock_item_id", db_column="item_id")
    qty_available = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False,
                                        default=Decimal("0"), editable=False)

    def __str__(self):
        return f"{self.company_id} · {self.item_id}: {self.qty_available}"

    class Meta:
        db_table = "stock"
        ordering = ["company_id", "item_id"]
        constraints = [
            models.UniqueConstraint(fields=["company_id", "item_id"], name="uq_stock_company_item"),
            models.CheckConstraint(condition=models.Q(qty_available__gte=0), name="ck_stock_not_negative"),
        ]
        permissions = [
            ("adjust_stock", "Puede ajustar el stock a mano"),
            ("view_all_stock", "Puede ver el stock de todas las empresas"),
        ]
