from django.conf import settings
from django.db import models

from enginedj.base.models import M_model_base


class M_device(M_model_base, models.Model):
    """Celular donde el conductor tiene la app: a dónde llegan sus notificaciones (token push de Expo)."""

    model_name = "device"

    platform_choices = [("android", "Android"), ("ios", "iOS")]

    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False, blank=False,
                                related_name="device_user_id", db_column="user_id")
    push_token = models.CharField(max_length=255, null=False, blank=False, unique=True,
                                  help_text="Token de Expo: ExponentPushToken[...].")
    platform = models.CharField(max_length=10, null=False, blank=True, default="android", choices=platform_choices)
    app_version = models.CharField(max_length=30, null=False, blank=True, default="")
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_id} · {self.platform}"

    class Meta:
        db_table = "device"
