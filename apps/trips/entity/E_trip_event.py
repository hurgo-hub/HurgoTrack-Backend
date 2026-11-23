from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.utils import timezone

from apps.core.entity import E_audit_base


class E_trip_event(E_audit_base):

    def __init__(
        self,
        trip_id: Optional[int | dict] = None,
        trip_line_id: Optional[int | dict] = None,
        user_id: Optional[int | dict] = None,
        event_type: Optional[str] = None,
        event_date: Optional[datetime] = None,
        from_state: Optional[str] = '',
        to_state: Optional[str] = '',
        name: Optional[str] = None,
        description: Optional[str] = '',
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.trip_id = trip_id or kwargs.get("trip_id_id")
        self.trip_line_id = trip_line_id or kwargs.get("trip_line_id_id")
        self.user_id = user_id or kwargs.get("user_id_id")
        self.event_type = event_type
        self.event_date = event_date if event_date is not None else timezone.now()
        self.from_state = from_state
        self.to_state = to_state
        self.name = name
        self.description = description
        self.latitude = latitude
        self.longitude = longitude
