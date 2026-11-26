from django.utils import timezone

from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.trips.entity import E_trip_line_serie
from apps.orders.models import M_trip_line_serie


class R_trip_line_serie(InvalidateAppsMixin, BaseRepositoryImpl[E_trip_line_serie]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_trip_line_serie, entity_class=E_trip_line_serie)
        self.model: M_trip_line_serie = self.model

    def registered_count(self, allocation) -> int:
        """Unidades registradas (no devueltas) de una asignación."""
        return self.model.objects.filter(order_line_trip_id=allocation).exclude(state="returned").count()

    def vin_in_delivery_trip(self, vin) -> M_trip_line_serie | None:
        """La moto ya va (o ya se entregó) en un viaje de entrega no cancelado."""
        return (
            self.model.objects.filter(vin=vin, trip_line_id__trip_id__trip_type="delivery")
            .exclude(state="returned")
            .exclude(trip_line_id__trip_id__state="cancelled")
            .select_related("trip_line_id__trip_id")
            .first()
        )

    def create_serie(self, **fields) -> M_trip_line_serie:
        serie = self.model.objects.create(**fields)
        self._invalidate_list_cache()
        return serie

    def of_stop(self, stop):
        return self.model.objects.filter(trip_line_id=stop)

    def mark(self, stop, state, exclude_returned=True):
        qs = self.of_stop(stop)
        if exclude_returned:
            qs = qs.exclude(state="returned")
        qs.update(state=state, update_date=timezone.now())
        self._invalidate_list_cache()
