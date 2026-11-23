from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_order_line(E_model_base):

    def __init__(
        self,
        order_id: Optional[int | dict] = None,
        item_id: Optional[int | dict] = None,
        recipient_id: Optional[int | dict] = None,
        address_id: Optional[int | dict] = None,
        qty: Optional[Decimal] = None,
        qty_assigned: Optional[Decimal] = Decimal('0'),
        qty_delivered: Optional[Decimal] = Decimal('0'),
        state: Optional[str] = 'pending',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.order_id = order_id or kwargs.get("order_id_id")
        self.item_id = item_id or kwargs.get("item_id_id")
        self.recipient_id = recipient_id or kwargs.get("recipient_id_id")
        self.address_id = address_id or kwargs.get("address_id_id")
        self.qty = qty
        self.qty_assigned = qty_assigned
        self.qty_delivered = qty_delivered
        self.state = state
