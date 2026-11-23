from django.db import models

from enginedj.base.models import M_model_base


class M_order(M_model_base, models.Model):
    """``order_dtd`` del .mwb: pedido de una empresa cliente.

    El destino (destinatario + dirección) va en cada línea, como en
    ``order_dtd_line``; la cabecera lleva la dirección de cargue.
    """

    model_name = "order"
    letter = "P"  # código P-XXXXXX que genera M_model_base

    state_choices = [
        ("draft", "Borrador"),
        ("requested", "Pedido"),
        ("confirmed", "Confirmado"),
        ("in_progress", "En despacho"),
        ("delivered", "Entregado"),
        ("cancelled", "Cancelado"),
    ]

    code = models.CharField(max_length=20, null=False, blank=False, unique=True, editable=False)
    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="order_company_id", db_column="company_id",
                                   help_text="Empresa cliente que pide.")
    address_id = models.ForeignKey("locations.M_address", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="order_address_id", db_column="address_id",
                                   help_text="Dirección de cargue de la empresa cliente.")
    order_date = models.DateField(null=False, blank=False, help_text="date del .mwb.")
    state = models.CharField(max_length=15, null=False, blank=False, choices=state_choices, default="requested",
                             db_index=True)
    odoo_purchase = models.CharField(max_length=60, null=False, blank=True, default="",
                                     help_text="purchase_odoo del .mwb: referencia de la compra en Odoo.")
    confirmed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return self.code

    class Meta:
        db_table = "orders"  # "order" es palabra reservada en SQL
        ordering = ["-order_date", "-id"]
        permissions = [
            ("create_any_company_order", "Puede crear pedidos para cualquier empresa cliente"),
            ("submit_order", "Puede enviar pedidos a Hurgo"),
            ("confirm_order", "Puede confirmar pedidos (compra en Odoo)"),
            ("cancel_order", "Puede cancelar pedidos antes de confirmar"),
            ("cancel_confirmed_order", "Puede cancelar pedidos confirmados"),
            ("view_all_order", "Puede ver pedidos de todas las empresas"),
        ]
