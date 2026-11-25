from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_purchase_request_line(E_model_base):

    def __init__(
        self,
        purchase_request_id: Optional[int | dict] = None,
        item_id: Optional[int | dict] = None,
        qty=None,
        order_line_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.purchase_request_id = purchase_request_id or kwargs.get("purchase_request_id_id")
        self.item_id = item_id or kwargs.get("item_id_id")
        self.qty = qty
        self.order_line_id = order_line_id or kwargs.get("order_line_id_id")
