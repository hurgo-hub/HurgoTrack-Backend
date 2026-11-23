from decimal import Decimal
from typing import Optional

from apps.core.entity import E_audit_base


class E_trip_attach(E_audit_base):

    def __init__(
        self,
        trip_id: Optional[int | dict] = None,
        trip_line_id: Optional[int | dict] = None,
        trip_event_id: Optional[int | dict] = None,
        type_attach_id: Optional[int | dict] = None,
        file: Optional[str] = None,
        description: Optional[str] = '',
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.trip_id = trip_id or kwargs.get("trip_id_id")
        self.trip_line_id = trip_line_id or kwargs.get("trip_line_id_id")
        self.trip_event_id = trip_event_id or kwargs.get("trip_event_id_id")
        self.type_attach_id = type_attach_id or kwargs.get("type_attach_id_id")
        self.file = file
        self.description = description
        self.latitude = latitude
        self.longitude = longitude
