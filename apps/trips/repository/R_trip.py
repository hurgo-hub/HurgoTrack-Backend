from django.db.models import Max, Prefetch, Sum

from enginedj.base.repository import BaseRepositoryImpl

from apps.core.cache import InvalidateAppsMixin
from apps.trips.entity import E_trip
from apps.trips.models import M_trip, M_trip_event, M_trip_line

BUSY_STATES = ("assigned", "in_route", "delivering")
LIST_RELATED = ("company_id", "brand_id", "vehicle_id", "driver_id__user_id", "origin_address_id", "parent_trip_id")


class R_trip(InvalidateAppsMixin, BaseRepositoryImpl[E_trip]):

    def __init__(self):
        super().__init__(model=M_trip, entity_class=E_trip)
        self.model: M_trip = self.model

    def get_for_update(self, trip_id) -> M_trip | None:
        # Sin select_related: FOR UPDATE no se aplica sobre FKs nulas (outer join) en PostgreSQL.
        return self.model.objects.select_for_update().filter(pk=trip_id, is_active=True).first()

    def create_trip(self, **fields) -> M_trip:
        trip = self.model.objects.create(**fields)
        self._invalidate_list_cache()
        return trip

    def save_trip(self, trip: M_trip, user, update_fields=None):
        trip.update_user_id = user
        if update_fields:
            trip.save(update_fields=[*update_fields, "update_user_id", "update_date"])
        else:
            trip.save()
        self._invalidate_list_cache()

    def set_state(self, trip: M_trip, new_state: str, user, **fields) -> str:
        """Cambia el estado (y campos extra) y devuelve el estado anterior."""
        old_state = trip.state
        trip.state = new_state
        for name, value in fields.items():
            setattr(trip, name, value)
        self.save_trip(trip, user)
        return old_state

    def busy_trip_for(self, exclude_trip, vehicle=None, driver=None) -> M_trip | None:
        """Otro viaje activo que ya usa el vehículo o el conductor."""
        qs = self.model.objects.filter(state__in=BUSY_STATES, is_active=True).exclude(pk=exclude_trip.pk)
        if vehicle is not None:
            qs = qs.filter(vehicle_id=vehicle)
        if driver is not None:
            qs = qs.filter(driver_id=driver)
        return qs.first()

    @staticmethod
    def stops(trip: M_trip):
        return M_trip_line.objects.filter(trip_id=trip)

    def has_stops(self, trip) -> bool:
        return self.stops(trip).exists()

    def next_sequence(self, trip) -> int:
        return (self.stops(trip).aggregate(m=Max("sequence"))["m"] or 0) + 1

    def total_weight(self, trip):
        return self.stops(trip).aggregate(s=Sum("weight_kg"))["s"] or 0

    def all_stops_finished(self, trip) -> bool:
        return not self.stops(trip).exclude(state__in=["delivered", "returned"]).exists()

    def active_return_trip_for(self, trip_line) -> M_trip | None:
        return self.model.objects.filter(returned_line_id=trip_line, is_active=True).exclude(state="cancelled").first()

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def visible(self, scope: dict | None):
        """Viajes activos filtrados por el alcance del usuario (None = todos)."""
        qs = self.model.objects.filter(is_active=True)
        return qs.filter(**scope) if scope else qs

    def with_list(self, qs):
        return qs.select_related(*LIST_RELATED)

    def with_detail(self, qs):
        from apps.orders.models import M_order_line_trip

        return qs.select_related(*LIST_RELATED).prefetch_related(
            Prefetch(
                "trip_line_trip_id",
                queryset=M_trip_line.objects.select_related("recipient_id", "address_id__location_id").prefetch_related(
                    "trip_line_serie_trip_line_id",
                    Prefetch(
                        "order_line_trip_trip_line_id",
                        queryset=M_order_line_trip.objects.select_related(
                            "order_line_id__order_id", "order_line_id__item_id"
                        ),
                    ),
                ),
            ),
            Prefetch("trip_event_trip_id", queryset=M_trip_event.objects.select_related("user_id")),
            "trip_attach_trip_id__type_attach_id",
        )

    def active_for_driver_user(self, user):
        return self.with_list(
            self.model.objects.filter(is_active=True, driver_id__user_id=user, state__in=BUSY_STATES)
        ).order_by("planned_departure", "id")
