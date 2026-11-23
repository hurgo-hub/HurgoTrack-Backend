from django.db import models

from apps.core.models.model_base import M_catalog_base


class M_trip_type_attach(M_catalog_base, models.Model):
    """Tipo de adjunto (remisión firmada, novedad, devolución, cargue)."""

    model_name = "trip_type_attach"

    key = models.SlugField(max_length=40, null=False, blank=False, unique=True,
                           help_text="Clave fija que usa el código, ej. delivery_proof.")
    is_delivery_proof = models.BooleanField(default=False,
                                            help_text="Prueba de entrega (remisión firmada). Obligatoria para entregar.")

    class Meta(M_catalog_base.Meta):
        db_table = "trip_type_attach"
