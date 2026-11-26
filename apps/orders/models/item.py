from django.db import models

from enginedj.base.models import M_model_base


class M_item(M_model_base, models.Model):
    """Producto. ``company_id`` (base_idbase del .mwb): empresa cliente dueña del catálogo."""

    model_name = "item"


    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="item_company_id", db_column="company_id")
    type_item_id = models.ForeignKey("orders.M_type_item", on_delete=models.PROTECT, null=False, blank=False,
                                     related_name="item_type_item_id", db_column="type_item_id")
    brand_id = models.ForeignKey("orders.M_brand", on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="item_brand_id", db_column="brand_id")
    sku = models.CharField(max_length=60, null=False, blank=True, default="", help_text="Referencia interna / Odoo.")
    odoo_ref = models.CharField(max_length=60, null=False, blank=True, default="", db_index=True,
                                help_text="ID del producto (product.product) en Odoo.")
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.TextField(null=False, blank=True, default="")
    unit_id = models.ForeignKey("orders.M_unit", on_delete=models.PROTECT, null=True, blank=True,
                                related_name="item_unit_id", db_column="unit_id",
                                help_text="Unidad de la empresa.")
    weight_kg = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, help_text="Peso unitario.")
    is_vehicle = models.BooleanField(default=False, help_text="El producto es un vehículo (moto).")
    is_serialized = models.BooleanField(default=False, help_text="is_serie del .mwb: se despacha por VIN.")
    loading_tags = models.ManyToManyField("locations.M_loading_tag", blank=True, related_name="item_loading_tags",
                                          db_table="item_loading_tag",
                                          help_text="Etiquetas para sugerir dónde se carga el producto.")

    @property
    def unit(self) -> str:
        """Código de la unidad (bulto, kg...), como lo usan los listados."""
        return self.unit_id.symbol if self.unit_id_id else "und"

    @unit.setter
    def unit(self, symbol: str):
        """Asigna una unidad de la empresa por su abreviatura (bulto, kg...)."""
        from apps.orders.models.unit import M_unit

        found = M_unit.objects.filter(symbol=symbol, company_id=self.company_id_id).first()
        if found is None:
            raise ValueError(f"La unidad '{symbol}' no existe en la empresa.")
        self.unit_id = found

    @property
    def uses_stock(self) -> bool:
        return self.type_item_id.uses_stock

    def __str__(self):
        return self.name

    class Meta:
        db_table = "item"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company_id", "sku"], condition=~models.Q(sku=""),
                                    name="uq_item_company_sku"),
        ]
