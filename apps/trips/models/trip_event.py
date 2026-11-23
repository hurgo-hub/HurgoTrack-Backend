from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models.model_base import M_audit_base


class M_trip_event(M_audit_base, models.Model):
    """Cada paso del viaje con fecha y responsable: cambios de estado y novedades."""

    model_name = "trip_event"

    event_type_choices = [
        ("state_change", "Cambio de estado"),
        ("novelty", "Novedad"),
        ("location", "Reporte de ubicación"),
        ("comment", "Comentario"),
    ]

    trip_id = models.ForeignKey("trips.M_trip", on_delete=models.CASCADE, null=False, blank=False,
                                related_name="trip_event_trip_id", db_column="trip_id")
    trip_line_id = models.ForeignKey("trips.M_trip_line", on_delete=models.CASCADE, null=True, blank=True,
                                     related_name="trip_event_trip_line_id", db_column="trip_line_id")
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=False, blank=False,
                                related_name="trip_event_user_id", db_column="user_id", help_text="Responsable.")
    event_type = models.CharField(max_length=15, null=False, blank=False, choices=event_type_choices)
    event_date = models.DateTimeField(null=False, blank=False, default=timezone.now, db_index=True)
    from_state = models.CharField(max_length=15, null=False, blank=True, default="")
    to_state = models.CharField(max_length=15, null=False, blank=True, default="")
    name = models.CharField(max_length=150, null=False, blank=False)
    description = models.TextField(null=False, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.trip_id} · {self.name}"

    class Meta:
        db_table = "trip_event"
        ordering = ["trip_id", "event_date", "id"]
