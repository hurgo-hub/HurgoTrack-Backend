from django.db.models import Prefetch

from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.orders.entity import E_order
from apps.orders.models import M_order, M_order_event, M_order_line, M_order_line_trip


class R_order(InvalidateAppsMixin, BaseRepositoryImpl[E_order]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_order, entity_class=E_order)
        self.model: M_order = self.model

    def get_for_update(self, order_id) -> M_order | None:
        return self.model.objects.select_for_update().filter(pk=order_id, is_active=True).first()

    def create_order(self, **fields) -> M_order:
        order = self.model.objects.create(**fields)
        self._invalidate_list_cache()
        return order

    def set_state(self, order: M_order, new_state: str, user, **fields) -> str:
        """Cambia el estado (y campos extra) y devuelve el estado anterior."""
        old_state = order.state
        order.state = new_state
        for name, value in fields.items():
            setattr(order, name, value)
        order.update_user = user
        order.save()
        self._invalidate_list_cache()
        return old_state

    def save_order(self, order: M_order, user):
        order.update_user = user
        order.save()
        self._invalidate_list_cache()

    def visible(self, company_ids=None):
        """Pedidos activos; ``company_ids=None`` = todas las empresas."""
        qs = self.model.objects.filter(is_active=True)
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        return qs

    def with_detail(self, qs):
        return qs.select_related("company_id", "address_id__location_id", "create_user").prefetch_related(
            Prefetch(
                "order_line_order_id",
                queryset=M_order_line.objects.select_related(
                    "item_id__brand_id", "recipient_id", "address_id__location_id"
                ).prefetch_related(
                    Prefetch(
                        "order_line_trip_order_line_id",
                        queryset=M_order_line_trip.objects.select_related("trip_line_id__trip_id").order_by("id"),
                    )
                ).order_by("id"),
            ),
            Prefetch("order_event_order_id", queryset=M_order_event.objects.select_related("user_id")),
        )
