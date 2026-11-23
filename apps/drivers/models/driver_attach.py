from django.db import models

from enginedj.base.models import M_model_base


class M_driver_attach(M_model_base, models.Model):
    model_name = "driver_attach"

    driver_id = models.ForeignKey("drivers.M_driver", on_delete=models.CASCADE, null=False, blank=False,
                                  related_name="driver_attach_driver_id", db_column="driver_id")
    name = models.CharField(max_length=150, null=False, blank=False, help_text="Ej. licencia, cédula, seguridad social.")
    file = models.FileField(upload_to="drivers/attachments/%Y/%m/", null=False, blank=False)
    date_expire = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "driver_attach"
