from django.db import models

from enginedj.base.models import M_catalog_base


class M_brand(M_catalog_base, models.Model):
    """Marca del producto (UMA, Auteco, AKT, Bera...). Regla: un viaje de motos lleva una sola marca.

    La crea cada empresa; ``company_id`` nulo = marca común. Nombre único por empresa.
    """

    model_name = "brand"

    name = models.CharField(max_length=120, null=False, blank=False)
    company_id = models.ForeignKey("base.M_company", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="brand_company_id", db_column="company_id",
                                   help_text="Empresa cliente dueña de la marca; vacío = común.")

    class Meta(M_catalog_base.Meta):
        db_table = "brand"
        constraints = [
            models.UniqueConstraint(fields=["company_id", "name"], name="uq_brand_company_name"),
            models.UniqueConstraint(fields=["name"], condition=models.Q(company_id__isnull=True),
                                    name="uq_brand_common_name"),
        ]
