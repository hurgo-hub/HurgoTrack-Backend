from django.db import models

from enginedj.base.models import M_model_base


class M_country(M_model_base, models.Model):
    model_name = "country"

    iso_code = models.CharField(max_length=3, null=False, blank=False, unique=True, help_text="code_country del .mwb, ej. CO.")
    name = models.CharField(max_length=120, null=False, blank=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "country"
        ordering = ["name"]
