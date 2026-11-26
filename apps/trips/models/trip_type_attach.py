from django.db import models
from django.utils.text import slugify

from enginedj.base.models import M_catalog_base

# Tipos que usa el código (los crea el seed de trips); no se desactivan
SYSTEM_KEYS = {"delivery_proof", "novelty", "return", "loading"}


class M_trip_type_attach(M_catalog_base, models.Model):
    """Documento del proceso de Hurgo (remisión, foto de cargue...) y la etapa en que se pide.

    Los documentos que exige cada empresa viven en su esquema (``orders.M_document_type``).
    - ``stage``: ``loading`` (al cargar, antes de salir), ``delivery`` (al entregar),
      ``return`` (devolución), ``novelty`` (novedad).
    - ``is_required``: sin él no se puede pasar esa etapa (salir o entregar).
    """

    model_name = "trip_type_attach"

    stage_choices = [
        ("loading", "Cargue"),
        ("delivery", "Entrega"),
        ("return", "Devolución"),
        ("novelty", "Novedad"),
    ]

    key = models.SlugField(max_length=60, null=False, blank=False, unique=True,
                           help_text="Clave única; la de los de sistema la usa el código, ej. delivery_proof.")
    stage = models.CharField(max_length=10, null=False, blank=False, choices=stage_choices, default="delivery",
                             db_index=True)
    is_required = models.BooleanField(default=False, help_text="Obligatorio para pasar la etapa.")
    is_delivery_proof = models.BooleanField(default=False,
                                            help_text="Prueba de entrega (remisión firmada). Obligatoria para entregar.")

    @property
    def is_system(self) -> bool:
        return self.key in SYSTEM_KEYS

    def save(self, *args, **kwargs):
        if not self.key:
            base = slugify(f"hurgo-{self.name}")[:50] or "doc"
            key, n = base, 1
            while M_trip_type_attach.objects.filter(key=key).exclude(pk=self.pk).exists():
                n += 1
                key = f"{base}-{n}"
            self.key = key
        super().save(*args, **kwargs)

    class Meta(M_catalog_base.Meta):
        db_table = "trip_type_attach"
