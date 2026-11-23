from django.db import models

from enginedj.base.models import M_model_base


class M_odoo_purchase(M_model_base, models.Model):
    """Copia local de una compra (purchase.order) de Odoo, la que se confirma en el paso 2."""

    model_name = "odoo_purchase"

    odoo_id = models.PositiveIntegerField(null=False, blank=False, unique=True)
    name = models.CharField(max_length=60, null=False, blank=False, db_index=True, help_text="Ej. P00012.")
    partner_odoo_id = models.PositiveIntegerField(null=True, blank=True)
    partner_name = models.CharField(max_length=200, null=False, blank=True, default="")
    state = models.CharField(max_length=30, null=False, blank=True, default="",
                             help_text="Estado en Odoo: draft, sent, to approve, purchase, done, cancel.")
    date_order = models.DateTimeField(null=True, blank=True)
    amount_total = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    raw = models.JSONField(null=False, blank=True, default=dict, help_text="Respuesta completa de Odoo.")
    synced_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "odoo_purchase"
        ordering = ["-odoo_id"]
