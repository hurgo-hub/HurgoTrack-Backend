from django.db import models

from enginedj.base.models import M_model_base


class M_address(M_model_base, models.Model):
    """Dirección de una empresa: bodega de cargue o punto de entrega."""

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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.address}"

    class Meta:
        db_table = "address"
        ordering = ["name"]
