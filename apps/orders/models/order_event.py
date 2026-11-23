from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models.model_base import M_audit_base


class M_order_event(M_audit_base, models.Model):
    """Historial del pedido: cada paso con fecha y responsable (lo ve el cliente)."""

    model_name = "order_event"

    order_id = models.ForeignKey("orders.M_order", on_delete=models.CASCADE, null=False, blank=False,
                                 related_name="order_event_order_id", db_column="order_id")
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=False, blank=False,
                                related_name="order_event_user_id", db_column="user_id")
    event_date = models.DateTimeField(null=False, blank=False, default=timezone.now, db_index=True)
    from_state = models.CharField(max_length=15, null=False, blank=True, default="")
    to_state = models.CharField(max_length=15, null=False, blank=True, default="")
    name = models.CharField(max_length=150, null=False, blank=False)
    description = models.TextField(null=False, blank=True, default="")

    def __str__(self):
        return f"{self.order_id} · {self.name}"

    class Meta:
        db_table = "order_event"
        ordering = ["order_id", "event_date", "id"]
