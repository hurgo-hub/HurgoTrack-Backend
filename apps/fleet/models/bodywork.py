from django.db import models

from apps.core.models.model_base import M_catalog_base


class M_bodywork(M_catalog_base, models.Model):
    """Carrocería.

    official_code es el code del .mwb (código del Ministerio / RNDC). No se
    llama code porque M_model_base autogenera ese campo al crear.
    """

    model_name = "bodywork"

    official_code = models.CharField(max_length=20, null=False, blank=False, unique=True)

    class Meta(M_catalog_base.Meta):
        db_table = "bodywork"
