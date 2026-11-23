from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.orders.entity import E_order_event
from apps.orders.models import M_order_event


class R_order_event(InvalidateAppsMixin, BaseRepositoryImpl[E_order_event]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_order_event, entity_class=E_order_event)
        self.model: M_order_event = self.model

    def register(self, order, user, name, from_state="", to_state="", description="") -> M_order_event:
        event = self.model.objects.create(
            order_id=order, user_id=user, create_user=user, name=name,
            from_state=from_state, to_state=to_state, description=description or "",
        )
        self._invalidate_list_cache()
        return event
