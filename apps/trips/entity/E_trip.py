from datetime import datetime
from typing import Optional

from apps.core.entity import E_audit_base


class E_trip(E_audit_base):

    def __init__(
        self,
        code: Optional[str] = None,
        company_id: Optional[int | dict] = None,
        trip_type: Optional[str] = 'delivery',
        state: Optional[str] = 'draft',
        brand_id: Optional[int | dict] = None,
        carrier_id: Optional[int | dict] = None,
        vehicle_id: Optional[int | dict] = None,
        driver_id: Optional[int | dict] = None,
        origin_address_id: Optional[int | dict] = None,
        parent_trip_id: Optional[int | dict] = None,
        returned_line_id: Optional[int | dict] = None,
        planned_departure: Optional[datetime] = None,
        departure_date: Optional[datetime] = None,
        closed_date: Optional[datetime] = None,
        notes: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.code = code
        self.company_id = company_id or kwargs.get("company_id_id")
        self.trip_type = trip_type
        self.state = state
        self.brand_id = brand_id or kwargs.get("brand_id_id")
        self.carrier_id = carrier_id or kwargs.get("carrier_id_id")
        self.vehicle_id = vehicle_id or kwargs.get("vehicle_id_id")
        self.driver_id = driver_id or kwargs.get("driver_id_id")
        self.origin_address_id = origin_address_id or kwargs.get("origin_address_id_id")
        self.parent_trip_id = parent_trip_id or kwargs.get("parent_trip_id_id")
        self.returned_line_id = returned_line_id or kwargs.get("returned_line_id_id")
        self.planned_departure = planned_departure
        self.departure_date = departure_date
        self.closed_date = closed_date
        self.notes = notes
