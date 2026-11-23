from django.db import models

from enginedj.base.models import M_catalog_base


class M_brand(M_catalog_base, models.Model):
    """Marca del producto (UMA, Auteco, AKT, Bera...). Regla: un viaje de motos lleva una sola marca."""

    model_name = "brand"

    company_id = models.ForeignKey("base.M_company", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="brand_company_id", db_column="company_id",
                                   help_text="Empresa cliente dueña de la marca, si aplica.")

    class Meta(M_catalog_base.Meta):
        db_table = "brand"
