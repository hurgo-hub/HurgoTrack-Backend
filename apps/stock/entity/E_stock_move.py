from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_stock_move(E_model_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        item_id: Optional[int | dict] = None,
        move_type=None,
        qty=None,
        balance=None,
        move_date=None,
        odoo_purchase_line_id: Optional[int | dict] = None,
        purchase_request_id: Optional[int | dict] = None,
        order_line_trip_id: Optional[int | dict] = None,
        description='',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.item_id = item_id or kwargs.get("item_id_id")
        self.move_type = move_type
        self.qty = qty
        self.balance = balance
        self.move_date = move_date
        self.odoo_purchase_line_id = odoo_purchase_line_id or kwargs.get("odoo_purchase_line_id_id")
        self.purchase_request_id = purchase_request_id or kwargs.get("purchase_request_id_id")
        self.order_line_trip_id = order_line_trip_id or kwargs.get("order_line_trip_id_id")
        self.description = description
