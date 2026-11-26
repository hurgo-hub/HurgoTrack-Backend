from django.db import models

from enginedj.base.models import M_model_base


class M_order_attach(M_model_base, models.Model):
    """Documento subido al pedido (etapa ``order``), del tipo que exige la empresa o Hurgo."""

    model_name = "order_attach"

    order_id = models.ForeignKey("orders.M_order", on_delete=models.CASCADE, null=False, blank=False,
                                 related_name="order_attach_order_id", db_column="order_id")
    type_attach_id = models.ForeignKey("trips.M_trip_type_attach", on_delete=models.PROTECT, null=False,
                                       blank=False, related_name="order_attach_type_attach_id",
                                       db_column="type_attach_id")
    file = models.FileField(upload_to="orders/%Y/%m/", null=False, blank=False)
    description = models.CharField(max_length=255, null=False, blank=True, default="")

    def __str__(self):
        return f"{self.order_id} · {self.type_attach_id}"

    class Meta:
        db_table = "order_attach"
        ordering = ["order_id", "id"]
