from django.db import models

from enginedj.base.models import M_catalog_base


class M_brand_vehicle(M_catalog_base, models.Model):
    """Marca del vehículo."""

    model_name = "brand_vehicle"

    class Meta(M_catalog_base.Meta):
        db_table = "brand_vehicle"
