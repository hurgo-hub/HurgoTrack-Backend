from django.db import models

from enginedj.base.models import M_catalog_base


class M_type_vehicle(M_catalog_base, models.Model):
    """Tipo de vehículo."""

    model_name = "type_vehicle"

    class Meta(M_catalog_base.Meta):
        db_table = "type_vehicle"
