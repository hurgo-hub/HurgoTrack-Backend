from django.db.models import Sum

from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.orders.entity import E_order_line_trip
from apps.orders.models import M_order_line_trip


class R_order_line_trip(InvalidateAppsMixin, BaseRepositoryImpl[E_order_line_trip]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_order_line_trip, entity_class=E_order_line_trip)
        self.model: M_order_line_trip = self.model

    def add_qty(self, order_line, trip_line, qty, user) -> M_order_line_trip:
        allocation, created = self.model.objects.get_or_create(
            order_line_id=order_line, trip_line_id=trip_line, defaults={"qty": qty, "create_user": user}
        )
        if not created:
            allocation.qty += qty
            allocation.update_user = user
            allocation.save()
        self._invalidate_list_cache()
        return allocation

    def of_trip(self, trip):
        return self.model.objects.filter(trip_line_id__trip_id=trip)

    def items_of_trip(self, trip) -> list:
        return [a.order_line_id.item_id for a in self.of_trip(trip).select_related("order_line_id__item_id")]

    def order_line_ids_of_trip(self, trip):
        return self.of_trip(trip).values_list("order_line_id", flat=True)

    def order_line_ids_of_stop(self, trip_line):
        return self.model.objects.filter(trip_line_id=trip_line).values_list("order_line_id", flat=True)

    def get_in_stop(self, allocation_id, trip_line) -> M_order_line_trip | None:
        return (
            self.model.objects.select_related("order_line_id__item_id")
            .filter(pk=allocation_id, trip_line_id=trip_line)
            .first()
        )

    def serialized_of_trip(self, trip):
        return self.of_trip(trip).filter(order_line_id__item_id__is_serialized=True).select_related(
            "order_line_id__item_id", "trip_line_id"
        )

    def motorcycles_of_trip(self, trip):
        return self.of_trip(trip).filter(order_line_id__item_id__is_vehicle=True).aggregate(s=Sum("qty"))["s"] or 0
