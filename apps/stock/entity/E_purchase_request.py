from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_purchase_request(E_model_base):

    def __init__(
        self,
        code=None,
        company_id: Optional[int | dict] = None,
        state='sent',
        sent_date=None,
        purchased_date=None,
        notes='',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.code = code
        self.company_id = company_id or kwargs.get("company_id_id")
        self.state = state
        self.sent_date = sent_date
        self.purchased_date = purchased_date
        self.notes = notes
