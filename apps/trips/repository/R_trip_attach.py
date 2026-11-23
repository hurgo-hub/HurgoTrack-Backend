from enginedj.base.repository import BaseRepositoryImpl

from apps.core.cache import InvalidateAppsMixin
from apps.trips.entity import E_trip_attach
from apps.trips.models import M_trip_attach


class R_trip_attach(InvalidateAppsMixin, BaseRepositoryImpl[E_trip_attach]):

    def __init__(self):
        super().__init__(model=M_trip_attach, entity_class=E_trip_attach)
        self.model: M_trip_attach = self.model

    def attach(self, trip, file, attach_type, user, line=None, event=None, latitude=None, longitude=None):
        attach = self.model.objects.create(
            trip_id=trip, trip_line_id=line, trip_event_id=event, type_attach_id=attach_type, file=file,
            latitude=latitude, longitude=longitude, create_user_id=user,
        )
        self._invalidate_list_cache()
        return attach
