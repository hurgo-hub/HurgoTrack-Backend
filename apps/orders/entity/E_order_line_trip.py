from decimal import Decimal
from typing import Optional

from apps.core.entity import E_audit_base


class E_order_line_trip(E_audit_base):

    def __init__(
        self,
        order_line_id: Optional[int | dict] = None,
        trip_line_id: Optional[int | dict] = None,
        qty: Optional[Decimal] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.order_line_id = order_line_id or kwargs.get("order_line_id_id")
        self.trip_line_id = trip_line_id or kwargs.get("trip_line_id_id")
        self.qty = qty
