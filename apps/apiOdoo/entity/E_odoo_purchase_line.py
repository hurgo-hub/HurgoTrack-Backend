from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_odoo_purchase_line(E_model_base):

    def __init__(
        self,
        purchase_id: Optional[int | dict] = None,
        odoo_line_id: Optional[int] = None,
        product_odoo_id: Optional[int] = None,
        product_name: Optional[str] = '',
        item_id: Optional[int | dict] = None,
        product_qty: Optional[Decimal] = Decimal("0"),
        qty_received: Optional[Decimal] = Decimal("0"),
        uom_name: Optional[str] = '',
        qty_stocked: Optional[Decimal] = Decimal("0"),
        raw: Optional[dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.purchase_id = purchase_id or kwargs.get("purchase_id_id")
        self.odoo_line_id = odoo_line_id
        self.product_odoo_id = product_odoo_id
        self.product_name = product_name
        self.item_id = item_id or kwargs.get("item_id_id")
        self.product_qty = product_qty
        self.qty_received = qty_received
        self.uom_name = uom_name
        self.qty_stocked = qty_stocked
        self.raw = raw or {}
