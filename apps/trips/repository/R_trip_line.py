from django.utils import timezone

from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.trips.entity import E_trip_line
from apps.trips.models import M_trip_line


class R_trip_line(InvalidateAppsMixin, BaseRepositoryImpl[E_trip_line]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_trip_line, entity_class=E_trip_line)
        self.model: M_trip_line = self.model

    def get_for_update(self, trip, trip_line_id) -> M_trip_line | None:
        return self.model.objects.select_for_update().filter(pk=trip_line_id, trip_id=trip).first()

    def create_stop(self, **fields) -> M_trip_line:
        stop = self.model.objects.create(**fields)
        self._invalidate_list_cache()
        return stop

    def stops_by_destination(self, trip) -> dict:
        return {(s.recipient_id_id, s.address_id_id): s for s in self.model.objects.filter(trip_id=trip)}

    def save_stop(self, stop: M_trip_line, user):
        stop.update_user = user
        stop.save()
        self._invalidate_list_cache()

    def start_route(self, trip):
        self.model.objects.filter(trip_id=trip, state="pending").update(state="in_route", update_date=timezone.now())
        self._invalidate_list_cache()
