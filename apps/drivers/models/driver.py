from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from enginedj.base.choices import LICENSE_CATEGORY_CHOICES
from enginedj.base.models import M_model_base


class M_driver(M_model_base, models.Model):
    """``drive`` del .mwb. ``user_id`` es el login de la app móvil; nombre y documento van en auth.User + M_user_detail."""

    model_name = "driver"

    company_id = models.ForeignKey("base.M_company", on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="driver_company_id", db_column="company_id",
                                   help_text="Transportador con el que trabaja (Hurgo o independiente).")
    user_id = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=False, blank=False,
                                   related_name="driver_user_id", db_column="user_id")
    partner_id = models.ForeignKey("fleet.M_partner", on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="driver_partner_id", db_column="partner_id",
                                   help_text="Solo si el conductor también es propietario / tercero registrado.")
    license_number = models.CharField(max_length=30, null=False, blank=False, unique=True, help_text="n_license del .mwb.")
    license_category = models.CharField(max_length=2, null=False, blank=False, choices=LICENSE_CATEGORY_CHOICES,
                                        help_text="category del .mwb.")
    license_expedition = models.DateField(null=True, blank=True, help_text="data_expedition del .mwb.")
    license_expire = models.DateField(null=True, blank=True, db_index=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, null=False, blank=False, default=0,
                                         validators=[MinValueValidator(0), MaxValueValidator(5)], editable=False,
                                         help_text="Se recalcula con las calificaciones de las entregas.")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.user_id.get_full_name() or self.user_id.get_username()

    class Meta:
        db_table = "driver"
