from decimal import Decimal
from typing import Optional

from enginedj.base.entity import E_model_base


class E_item(E_model_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        type_item_id: Optional[int | dict] = None,
        brand_id: Optional[int | dict] = None,
        sku: Optional[str] = '',
        odoo_ref: Optional[str] = '',
        name: Optional[str] = None,
        description: Optional[str] = '',
        unit: Optional[str] = 'und',
        weight_kg: Optional[Decimal] = None,
        is_vehicle: Optional[bool] = False,
        is_serialized: Optional[bool] = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.type_item_id = type_item_id or kwargs.get("type_item_id_id")
        self.brand_id = brand_id or kwargs.get("brand_id_id")
        self.sku = sku
        self.odoo_ref = odoo_ref
        self.name = name
        self.description = description
        self.unit = unit
        self.weight_kg = weight_kg
        self.is_vehicle = is_vehicle
        self.is_serialized = is_serialized
