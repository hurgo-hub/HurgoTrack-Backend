from typing import Optional

from apps.core.entity import E_audit_base


class E_trip_line_serie(E_audit_base):

    def __init__(
        self,
        trip_line_id: Optional[int | dict] = None,
        order_line_trip_id: Optional[int | dict] = None,
        vin: Optional[str] = None,
        engine_number: Optional[str] = '',
        state: Optional[str] = 'pending',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.trip_line_id = trip_line_id or kwargs.get("trip_line_id_id")
        self.order_line_trip_id = order_line_trip_id or kwargs.get("order_line_trip_id_id")
        self.vin = vin
        self.engine_number = engine_number
        self.state = state
