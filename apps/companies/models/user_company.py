from django.conf import settings
from django.db import models

from apps.core.models.model_base import M_audit_base


class M_user_company(M_audit_base, models.Model):
    """``user_has_company`` del .mwb: empresas a las que pertenece el usuario (define qué puede ver)."""

    model_name = "user_company"

    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False,
                                related_name="user_company_user_id", db_column="user_id")
    company_id = models.ForeignKey("companies.M_company", on_delete=models.CASCADE, null=False, blank=False,
                                   related_name="user_company_company_id", db_column="company_id")

    def __str__(self):
        return f"{self.user_id} @ {self.company_id}"

    class Meta:
        db_table = "user_company"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "company_id"], name="uq_user_company"),
        ]
