from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_address(E_model_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        location_id: Optional[int | dict] = None,
        name: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = '',
        contact_name: Optional[str] = '',
        contact_phone: Optional[str] = '',
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.location_id = location_id or kwargs.get("location_id_id")
        self.name = name
        self.address = address
        self.description = description
        self.contact_name = contact_name
        self.contact_phone = contact_phone
        self.latitude = latitude
        self.longitude = longitude
