from enginedj.base.repository import BaseRepositoryImpl

from apps.core.cache import InvalidateAppsMixin
from apps.trips.entity import E_trip_event
from apps.trips.models import M_trip_event


class R_trip_event(InvalidateAppsMixin, BaseRepositoryImpl[E_trip_event]):

    def __init__(self):
        super().__init__(model=M_trip_event, entity_class=E_trip_event)
        self.model: M_trip_event = self.model

    def register(self, trip, user, name, event_type="state_change", line=None, from_state="", to_state="",
                 description="", latitude=None, longitude=None) -> M_trip_event:
        event = self.model.objects.create(
            trip_id=trip, trip_line_id=line, user_id=user, create_user_id=user, event_type=event_type,
            name=name, description=description or "", from_state=from_state, to_state=to_state,
            latitude=latitude, longitude=longitude,
        )
        self._invalidate_list_cache()
        return event
