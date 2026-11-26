from django.db import models

from enginedj.base.models import M_model_base


class M_address(M_model_base, models.Model):
    """Lugar de cargue (central, de Hurgo): planta, bodega o proveedor donde Hurgo carga.

    Lo registra despacho a nombre de la empresa dueña del sitio y se elige al gestionar el
    pedido; ``tags`` dice qué se carga ahí. Las direcciones de entrega de cada empresa viven en
    su propio esquema (``orders.M_company_address``).
    """

    model_name = "address"

    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="address_company_id", db_column="company_id")
    location_id = models.ForeignKey("locations.M_location", on_delete=models.PROTECT, null=False, blank=False,
                                    related_name="address_location_id", db_column="location_id",
                                    help_text="Municipio.")
    name = models.CharField(max_length=120, null=False, blank=False, help_text="Nombre corto, ej. 'Bodega principal'.")
    address = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=False, blank=True, default="", help_text="Indicaciones para llegar.")
    contact_name = models.CharField(max_length=150, null=False, blank=True, default="")
    contact_phone = models.CharField(max_length=40, null=False, blank=True, default="")
    tags = models.ManyToManyField("locations.M_loading_tag", blank=True, related_name="address_tags",
                                  db_table="loading_point_tag", help_text="Qué se carga en este lugar.")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.address}"

    class Meta:
        db_table = "loading_point"  # "address" es la tabla de direcciones en el esquema de cada empresa
        ordering = ["name"]
        permissions = [
            ("manage_loading_point", "Puede registrar lugares de cargue y sus etiquetas"),
        ]
