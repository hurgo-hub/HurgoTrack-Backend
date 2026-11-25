from django.db import models

from enginedj.base.models import M_catalog_base


class M_loading_tag(M_catalog_base, models.Model):
    """Etiqueta de cargue: qué se carga en un lugar (Cemento, Detergente, Motos...).

    Se pone en las direcciones de cargue (``M_address.tags``) y en los productos
    (``M_item.loading_tags``) para sugerir dónde cargar cada material.
    """

    model_name = "loading_tag"

    class Meta(M_catalog_base.Meta):
        db_table = "loading_tag"
