from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_stock(E_model_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        item_id: Optional[int | dict] = None,
        qty_available=Decimal('0'),
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.item_id = item_id or kwargs.get("item_id_id")
        self.qty_available = qty_available
