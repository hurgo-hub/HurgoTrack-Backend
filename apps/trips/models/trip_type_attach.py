from django.db import models
from django.utils.text import slugify

from enginedj.base.models import M_catalog_base

# Tipos que usa el código (los crea el seed de trips); no se desactivan
SYSTEM_KEYS = {"delivery_proof", "novelty", "return", "loading"}


class M_trip_type_attach(M_catalog_base, models.Model):
    """Tipo de documento / adjunto y la etapa del proceso en que se pide.

    - ``company_id`` nulo: lo define Hurgo y aplica a todas las empresas. Con empresa: lo pide
      esa empresa en sus solicitudes.
    - ``stage``: ``order`` (al crear/confirmar el pedido), ``loading`` (al cargar, antes de salir),
      ``delivery`` (al entregar), ``return`` (devolución), ``novelty`` (novedad).
    - ``is_required``: sin él no se puede pasar esa etapa (confirmar, salir o entregar).
    """

    model_name = "trip_type_attach"

    stage_choices = [
        ("order", "Pedido"),
        ("loading", "Cargue"),
        ("delivery", "Entrega"),
        ("return", "Devolución"),
        ("novelty", "Novedad"),
    ]

    name = models.CharField(max_length=120, null=False, blank=False)
    company_id = models.ForeignKey("base.M_company", on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="trip_type_attach_company_id", db_column="company_id",
                                   help_text="Empresa que lo exige; vacío = de Hurgo (todas).")
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
            base = slugify(f"{self.company_id_id or 'hurgo'}-{self.name}")[:50] or "doc"
            key, n = base, 1
            while M_trip_type_attach.objects.filter(key=key).exclude(pk=self.pk).exists():
                n += 1
                key = f"{base}-{n}"
            self.key = key
        super().save(*args, **kwargs)

    class Meta(M_catalog_base.Meta):
        db_table = "trip_type_attach"
        constraints = [
            models.UniqueConstraint(fields=["company_id", "name"], name="uq_trip_type_attach_company_name"),
            models.UniqueConstraint(fields=["name"], condition=models.Q(company_id__isnull=True),
                                    name="uq_trip_type_attach_common_name"),
        ]
