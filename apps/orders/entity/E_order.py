from datetime import date, datetime
from typing import Optional

from apps.core.entity import E_audit_base


class E_order(E_audit_base):

    def __init__(
        self,
        code: Optional[str] = None,
        company_id: Optional[int | dict] = None,
        address_id: Optional[int | dict] = None,
        order_date: Optional[date] = None,
        state: Optional[str] = 'requested',
        odoo_purchase: Optional[str] = '',
        confirmed_date: Optional[datetime] = None,
        notes: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.code = code
        self.company_id = company_id or kwargs.get("company_id_id")
        self.address_id = address_id or kwargs.get("address_id_id")
        self.order_date = order_date
        self.state = state
        self.odoo_purchase = odoo_purchase
        self.confirmed_date = confirmed_date
        self.notes = notes
