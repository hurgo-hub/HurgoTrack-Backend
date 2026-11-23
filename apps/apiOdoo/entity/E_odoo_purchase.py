from datetime import datetime
from decimal import Decimal
from typing import Optional

from apps.core.entity import E_audit_base


class E_odoo_purchase(E_audit_base):

    def __init__(
        self,
        odoo_id: Optional[int] = None,
        name: Optional[str] = None,
        partner_odoo_id: Optional[int] = None,
        partner_name: Optional[str] = '',
        state: Optional[str] = '',
        date_order: Optional[datetime] = None,
        amount_total: Optional[Decimal] = None,
        raw: Optional[dict] = None,
        synced_date: Optional[datetime] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.odoo_id = odoo_id
        self.name = name
        self.partner_odoo_id = partner_odoo_id
        self.partner_name = partner_name
        self.state = state
        self.date_order = date_order
        self.amount_total = amount_total
        self.raw = raw if raw is not None else {}
        self.synced_date = synced_date
