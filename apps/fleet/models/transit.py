from django.db import models

from apps.core.models.model_base import M_catalog_base


class M_transit(M_catalog_base, models.Model):
    """Organismo de tránsito donde está matriculado el vehículo.

    official_code es el code del .mwb (código del Ministerio / RNDC). No se
    llama code porque M_model_base autogenera ese campo al crear.
    """

    model_name = "transit"

    official_code = models.CharField(max_length=20, null=False, blank=False, unique=True)

    class Meta(M_catalog_base.Meta):
        db_table = "transit"
