from django.db import models

from enginedj.base.models import M_model_base


class M_purchase_request(M_model_base, models.Model):
    """Solicitud de compra que Hurgo le manda al facturador de la empresa (ej. Distritodo).

    El facturador compra en Odoo y registra la(s) compra(s) P000XX; al vincularlas, lo comprado
    entra al stock de la empresa. Una solicitud puede cubrirse con varias compras.
    """

    model_name = "purchase_request"
    letter = "SC"  # código SC-XXXXXX que genera M_model_base

    state_choices = [
        ("draft", "Borrador"),
        ("sent", "Enviada al facturador"),
        ("purchased", "Comprada"),
        ("cancelled", "Cancelada"),
    ]

    code = models.CharField(max_length=20, null=False, blank=False, unique=True, editable=False)
    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="purchase_request_company_id", db_column="company_id",
                                   help_text="Empresa que compra (dueña del stock).")
    state = models.CharField(max_length=15, null=False, blank=False, choices=state_choices, default="sent",
                             db_index=True)
    odoo_purchases = models.ManyToManyField("apiOdoo.M_odoo_purchase", blank=True,
                                            related_name="purchase_request_odoo_purchases",
                                            db_table="purchase_request_odoo_purchase",
                                            help_text="Compras de Odoo con que se cubrió.")
    sent_date = models.DateTimeField(null=True, blank=True)
    purchased_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return self.code

    class Meta:
        db_table = "purchase_request"
        ordering = ["-id"]
        permissions = [
            ("manage_purchase_request", "Puede crear, enviar y cancelar solicitudes de compra"),
            ("link_purchase_request", "Puede registrar la compra de Odoo de una solicitud"),
            ("view_all_purchase_request", "Puede ver las solicitudes de compra de todas las empresas"),
        ]
