from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.trips.entity import E_trip_type_attach
from apps.trips.models import M_trip_type_attach


class R_trip_type_attach(InvalidateAppsMixin, BaseRepositoryImpl[E_trip_type_attach]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_trip_type_attach, entity_class=E_trip_type_attach)
        self.model: M_trip_type_attach = self.model

    def get_by_key(self, key) -> M_trip_type_attach | None:
        return self.model.objects.filter(key=key, is_active=True).first()
