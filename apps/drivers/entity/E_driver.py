from datetime import date
from decimal import Decimal
from typing import Optional

from apps.core.entity import E_audit_base


class E_driver(E_audit_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        user_id: Optional[int | dict] = None,
        partner_id: Optional[int | dict] = None,
        license_number: Optional[str] = None,
        license_category: Optional[str] = None,
        license_expedition: Optional[date] = None,
        license_expire: Optional[date] = None,
        average_rating: Optional[Decimal] = Decimal('0'),
        is_available: Optional[bool] = True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.user_id = user_id or kwargs.get("user_id_id")
        self.partner_id = partner_id or kwargs.get("partner_id_id")
        self.license_number = license_number
        self.license_category = license_category
        self.license_expedition = license_expedition
        self.license_expire = license_expire
        self.average_rating = average_rating
        self.is_available = is_available
