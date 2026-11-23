from django.db import models

from enginedj.base.models import M_model_base


class M_odoo_sync_log(M_model_base, models.Model):
    """Bitácora de cada llamada a Odoo: qué se pidió, qué respondió y si falló."""

    model_name = "odoo_sync_log"

    status_choices = [
        ("success", "Exitoso"),
        ("error", "Error"),
    ]

    operation = models.CharField(max_length=60, null=False, blank=False, help_text="Ej. get_purchase, notify_delivery.")
    odoo_model = models.CharField(max_length=60, null=False, blank=True, default="")
    reference = models.CharField(max_length=120, null=False, blank=True, default="", db_index=True,
                                 help_text="Referencia local (código del pedido, nombre de la compra...).")
    status = models.CharField(max_length=10, null=False, blank=False, choices=status_choices)
    request = models.JSONField(null=False, blank=True, default=dict)
    response = models.JSONField(null=True, blank=True)
    error = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return f"{self.operation} {self.reference} ({self.status})"

    class Meta:
        db_table = "odoo_sync_log"
        ordering = ["-id"]
        permissions = [
            ("sync_odoo", "Puede sincronizar datos con Odoo"),
        ]
