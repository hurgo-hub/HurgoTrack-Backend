from django.db import models

from apps.core.models.model_base import M_audit_base


class M_country(M_audit_base, models.Model):
    model_name = "country"

    iso_code = models.CharField(max_length=3, null=False, blank=False, unique=True, help_text="code_country del .mwb, ej. CO.")
    name = models.CharField(max_length=120, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "country"
        ordering = ["name"]
