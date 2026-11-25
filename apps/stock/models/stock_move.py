from django.db import models
from django.utils import timezone

from enginedj.base.models import M_model_base


class M_stock_move(M_model_base, models.Model):
    """Kardex: cada entrada o salida del stock, con su origen (de dónde salió cada bolsa)."""

    model_name = "stock_move"

    type_choices = [
        ("purchase_in", "Entrada por compra en Odoo"),
        ("trip_out", "Cargue a viaje"),
        ("trip_cancel_in", "Devolución por viaje cancelado"),
        ("return_in", "Devolución de carga"),
        ("adjust", "Ajuste manual"),
    ]

    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="stock_move_company_id", db_column="company_id")
    item_id = models.ForeignKey("orders.M_item", on_delete=models.PROTECT, null=False, blank=False,
                                related_name="stock_move_item_id", db_column="item_id")
    move_type = models.CharField(max_length=20, null=False, blank=False, choices=type_choices, db_index=True)
    qty = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False,
                              help_text="Positivo = entra; negativo = sale.")
    balance = models.DecimalField(max_digits=14, decimal_places=2, null=False, blank=False,
                                  help_text="Stock disponible después del movimiento.")
    move_date = models.DateTimeField(null=False, blank=False, default=timezone.now, db_index=True)
    odoo_purchase_line_id = models.ForeignKey("apiOdoo.M_odoo_purchase_line", on_delete=models.PROTECT, null=True,
                                              blank=True, related_name="stock_move_odoo_purchase_line_id",
                                              db_column="odoo_purchase_line_id")
    purchase_request_id = models.ForeignKey("stock.M_purchase_request", on_delete=models.PROTECT, null=True,
                                            blank=True, related_name="stock_move_purchase_request_id",
                                            db_column="purchase_request_id")
    order_line_trip_id = models.ForeignKey("orders.M_order_line_trip", on_delete=models.SET_NULL, null=True,
                                           blank=True, related_name="stock_move_order_line_trip_id",
                                           db_column="order_line_trip_id",
                                           help_text="Cargue de una línea de pedido en un viaje.")
    description = models.CharField(max_length=255, null=False, blank=True, default="")

    def __str__(self):
        return f"{self.get_move_type_display()} {self.item_id} {self.qty}"

    class Meta:
        db_table = "stock_move"
        ordering = ["-move_date", "-id"]
