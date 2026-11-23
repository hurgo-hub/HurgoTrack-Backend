from django.conf import settings
from django.db import models

from apps.core.choices import DOCUMENT_TYPE_CHOICES
from apps.core.models.model_base import M_audit_base


class M_user_detail(M_audit_base, models.Model):
    """Datos del usuario que no trae auth.User (el ``user`` del .mwb es auth.User)."""

    model_name = "user_detail"

    user_id = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="user_detail_user_id", db_column="user_id")
    document_type = models.CharField(max_length=5, null=False, blank=False, choices=DOCUMENT_TYPE_CHOICES, default="CC")
    document_number = models.CharField(max_length=20, null=False, blank=True, default="")
    phone = models.CharField(max_length=40, null=False, blank=True, default="")
    avatar = models.FileField(upload_to="users/avatars/", null=True, blank=True)
    default_company_id = models.ForeignKey("companies.M_company", on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name="user_detail_default_company_id",
                                           db_column="default_company_id")

    def __str__(self):
        return f"Detalle de {self.user_id}"

    class Meta:
        db_table = "user_detail"
