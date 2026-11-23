from django.db import models

from enginedj.base.models import M_model_base


class M_trip_attach(M_model_base, models.Model):
    model_name = "trip_attach"

    trip_id = models.ForeignKey("trips.M_trip", on_delete=models.CASCADE, null=False, blank=False,
                                related_name="trip_attach_trip_id", db_column="trip_id")
    trip_line_id = models.ForeignKey("trips.M_trip_line", on_delete=models.CASCADE, null=True, blank=True,
                                     related_name="trip_attach_trip_line_id", db_column="trip_line_id")
    trip_event_id = models.ForeignKey("trips.M_trip_event", on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="trip_attach_trip_event_id", db_column="trip_event_id")
    type_attach_id = models.ForeignKey("trips.M_trip_type_attach", on_delete=models.PROTECT, null=False, blank=False,
                                       related_name="trip_attach_type_attach_id", db_column="type_attach_id",
                                       help_text="trip_type_attach_id del .mwb.")
    file = models.FileField(upload_to="trips/%Y/%m/", null=False, blank=False)
    description = models.CharField(max_length=255, null=False, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.type_attach_id} · {self.trip_id}"

    class Meta:
        db_table = "trip_attach"
