from django.db import models

from apps.core.choices import DOCUMENT_TYPE_CHOICES
from apps.core.models.model_base import M_audit_base


class M_company(M_audit_base, models.Model):
    """Empresa: cliente que pide (UMA, Auteco...), transportador (Hurgo o independiente) o destinatario."""

    model_name = "company"

    name = models.CharField(max_length=200, null=False, blank=False)
    document_type = models.CharField(max_length=5, null=False, blank=False, choices=DOCUMENT_TYPE_CHOICES, default="NIT")
    document_number = models.CharField(max_length=20, null=False, blank=False, unique=True,
                                       help_text="NIT sin dígito de verificación.")
    verification_digit = models.CharField(max_length=1, null=False, blank=True, default="")
    email = models.EmailField(null=False, blank=True, default="")
    phone = models.CharField(max_length=40, null=False, blank=True, default="")
    # Marca blanca (remisiones, guías, correos): logo, color, head, footer, eslogan del .mwb.
    logo = models.FileField(upload_to="companies/logos/", null=True, blank=True)
    color = models.CharField(max_length=7, null=False, blank=True, default="", help_text="Hexadecimal, ej. #0A5BD3.")
    header = models.TextField(null=False, blank=True, default="")
    footer = models.TextField(null=False, blank=True, default="")
    slogan = models.CharField(max_length=200, null=False, blank=True, default="")
    # is_company / is_freelance del .mwb, separados por rol de la empresa en la operación.
    is_client = models.BooleanField(default=False, help_text="Empresa cliente que crea pedidos.")
    is_carrier = models.BooleanField(default=False, help_text="Transportador: Hurgo o independiente.")
    is_freelance = models.BooleanField(default=False, help_text="Transportador independiente (fase 3).")
    is_recipient = models.BooleanField(default=False, help_text="Destinatario final (concesionario, obra...).")
    odoo_ref = models.CharField(max_length=60, null=False, blank=True, default="", db_index=True,
                                help_text="ID del contacto (res.partner) en Odoo.")

    def __str__(self):
        return self.name

    class Meta:
        db_table = "company"
        ordering = ["name"]
