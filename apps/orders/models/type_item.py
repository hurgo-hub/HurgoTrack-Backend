from django.db import models

from enginedj.base.models import M_catalog_base


class M_type_item(M_catalog_base, models.Model):
    """Tipo de producto (motos, materiales...). Lo crea cada empresa para sus productos.

    ``company_id`` nulo = tipo común (lo ven todas las empresas, solo lo edita Hurgo).
    El nombre es único por empresa.
    """

    model_name = "type_item"

    name = models.CharField(max_length=120, null=False, blank=False)
    company_id = models.ForeignKey("base.M_company", on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="type_item_company_id", db_column="company_id",
                                   help_text="Empresa dueña del tipo; vacío = común.")
    is_serialized = models.BooleanField(default=False,
                                        help_text="Sus unidades se registran una por una con número de serie (VIN).")

    uses_stock = models.BooleanField(default=False,
                                     help_text="Se carga desde el stock de la empresa (compras de Odoo): materiales.")

    class Meta(M_catalog_base.Meta):
        db_table = "type_item"
        constraints = [
            models.UniqueConstraint(fields=["company_id", "name"], name="uq_type_item_company_name"),
            models.UniqueConstraint(fields=["name"], condition=models.Q(company_id__isnull=True),
                                    name="uq_type_item_common_name"),
        ]
