from django.db import models

from enginedj.base.models import M_catalog_base


class M_type_item(M_catalog_base, models.Model):
    """Tipo de producto (motos, materiales...). Una línea de negocio nueva = un tipo nuevo."""

    model_name = "type_item"

    is_serialized = models.BooleanField(default=False,
                                        help_text="Sus unidades se registran una por una con número de serie (VIN).")

    class Meta(M_catalog_base.Meta):
        db_table = "type_item"
