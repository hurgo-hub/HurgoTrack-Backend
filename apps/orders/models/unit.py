from django.db import models

from enginedj.base.models import M_model_base


class M_unit(M_model_base, models.Model):
    """Unidad de medida de los productos (bulto, kg, und...). La crea cada empresa.

    ``company_id`` nulo = unidad común (und, kg, ton, bulto, m3). ``symbol`` es único por empresa.
    (No se llama ``code``: M_model_base llena solo ese campo con un consecutivo.)
    """

    model_name = "unit"

    company_id = models.ForeignKey("base.M_company", on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="unit_company_id", db_column="company_id",
                                   help_text="Empresa dueña de la unidad; vacío = común.")
    symbol = models.CharField(max_length=20, null=False, blank=False, help_text="Abreviatura, ej. bulto, kg.")
    name = models.CharField(max_length=60, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "unit"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company_id", "symbol"], name="uq_unit_company_symbol"),
            models.UniqueConstraint(fields=["symbol"], condition=models.Q(company_id__isnull=True),
                                    name="uq_unit_common_symbol"),
        ]
