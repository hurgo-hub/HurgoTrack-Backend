from django.db import models

from apps.core.choices import DOCUMENT_TYPE_CHOICES
from apps.core.models.model_base import M_audit_base


class M_partner(M_audit_base, models.Model):
    """Tercero (persona o empresa): propietario o tenedor de vehículos."""

    model_name = "partner"

    company_id = models.ForeignKey("companies.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="partner_company_id", db_column="company_id",
                                   help_text="Empresa que lo registró (Hurgo o un transportador).")
    name = models.CharField(max_length=200, null=False, blank=False)
    is_company = models.BooleanField(default=False, help_text="True si es persona jurídica.")
    document_type = models.CharField(max_length=5, null=False, blank=False, choices=DOCUMENT_TYPE_CHOICES, default="CC")
    document_number = models.CharField(max_length=20, null=False, blank=False)
    email = models.EmailField(null=False, blank=True, default="")
    phone = models.CharField(max_length=40, null=False, blank=True, default="")
    address = models.CharField(max_length=255, null=False, blank=True, default="")
    location_id = models.ForeignKey("locations.M_location", on_delete=models.PROTECT, null=True, blank=True,
                                    related_name="partner_location_id", db_column="location_id")

    def __str__(self):
        return f"{self.name} ({self.document_number})"

    class Meta:
        db_table = "partner"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company_id", "document_number"], name="uq_partner_company_document"),
        ]
