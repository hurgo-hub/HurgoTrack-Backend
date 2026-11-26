from django.db import models

from enginedj.base.models import M_model_base
from apps.companies.uploads import PrivateUpload


class M_document_type(M_model_base, models.Model):
    """Documento que exige la empresa y en qué etapa (vive en su esquema; lo crea ella).

    ``stage``: ``order`` (para confirmar el pedido), ``loading`` (antes de salir), ``delivery``
    (antes de entregar), ``return`` (devolución), ``novelty`` (novedad).
    """

    model_name = "document_type"

    stage_choices = [
        ("order", "Pedido"),
        ("loading", "Cargue"),
        ("delivery", "Entrega"),
        ("return", "Devolución"),
        ("novelty", "Novedad"),
    ]

    company_id = models.ForeignKey("base.M_company", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="document_type_company_id", db_column="company_id")
    name = models.CharField(max_length=120, null=False, blank=False)
    stage = models.CharField(max_length=10, null=False, blank=False, choices=stage_choices, default="order")
    is_required = models.BooleanField(default=False, help_text="Obligatorio para pasar la etapa.")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "document_type"
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["company_id", "name"], name="uq_document_type_name")]


class M_document_file(M_model_base, models.Model):
    """Archivo de un documento de la empresa: del pedido, o del cargue / la entrega de un viaje."""

    model_name = "document_file"

    document_type_id = models.ForeignKey("orders.M_document_type", on_delete=models.PROTECT, null=False,
                                         blank=False, related_name="document_file_document_type_id",
                                         db_column="document_type_id")
    order_id = models.ForeignKey("orders.M_order", on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="document_file_order_id", db_column="order_id")
    trip_id = models.ForeignKey("trips.M_trip", on_delete=models.CASCADE, null=True, blank=True,
                                related_name="document_file_trip_id", db_column="trip_id")
    trip_line_id = models.ForeignKey("trips.M_trip_line", on_delete=models.CASCADE, null=True, blank=True,
                                     related_name="document_file_trip_line_id", db_column="trip_line_id")
    file = models.FileField(upload_to=PrivateUpload("companies"), null=False, blank=False)
    description = models.CharField(max_length=255, null=False, blank=True, default="")

    def __str__(self):
        return f"{self.document_type_id} · {self.file.name}"

    class Meta:
        db_table = "document_file"
        ordering = ["id"]
