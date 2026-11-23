from datetime import datetime
from decimal import Decimal
from typing import Optional

from apps.core.entity import E_audit_base


class E_trip_line(E_audit_base):

    def __init__(
        self,
        trip_id: Optional[int | dict] = None,
        sequence: Optional[int] = 1,
        recipient_id: Optional[int | dict] = None,
        address_id: Optional[int | dict] = None,
        estimated_date: Optional[datetime] = None,
        delivery_date: Optional[datetime] = None,
        qty: Optional[Decimal] = Decimal('0'),
        weight_kg: Optional[Decimal] = Decimal('0'),
        state: Optional[str] = 'pending',
        is_return: Optional[bool] = False,
        return_reason: Optional[str] = '',
        rating: Optional[int] = None,
        comment: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.trip_id = trip_id or kwargs.get("trip_id_id")
        self.sequence = sequence
        self.recipient_id = recipient_id or kwargs.get("recipient_id_id")
        self.address_id = address_id or kwargs.get("address_id_id")
        self.estimated_date = estimated_date
        self.delivery_date = delivery_date
        self.qty = qty
        self.weight_kg = weight_kg
        self.state = state
        self.is_return = is_return
        self.return_reason = return_reason
        self.rating = rating
        self.comment = comment
