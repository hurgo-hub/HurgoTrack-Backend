from decimal import Decimal
from typing import Optional

from apps.core.entity import E_audit_base


class E_vehicle(E_audit_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        plate: Optional[str] = None,
        brand_vehicle_id: Optional[int | dict] = None,
        type_vehicle_id: Optional[int | dict] = None,
        bodywork_id: Optional[int | dict] = None,
        transit_id: Optional[int | dict] = None,
        model_year: Optional[int] = None,
        color: Optional[str] = '',
        load_capacity_kg: Optional[Decimal] = None,
        empty_weight_kg: Optional[Decimal] = None,
        motorcycle_capacity: Optional[int] = None,
        vin: Optional[str] = '',
        fuel_type: Optional[str] = '',
        license_category: Optional[str] = '',
        transmission: Optional[str] = '',
        plate_transit_free: Optional[bool] = False,
        owner_id: Optional[int | dict] = None,
        holder_id: Optional[int | dict] = None,
        default_driver_id: Optional[int | dict] = None,
        is_available: Optional[bool] = True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.plate = plate
        self.brand_vehicle_id = brand_vehicle_id or kwargs.get("brand_vehicle_id_id")
        self.type_vehicle_id = type_vehicle_id or kwargs.get("type_vehicle_id_id")
        self.bodywork_id = bodywork_id or kwargs.get("bodywork_id_id")
        self.transit_id = transit_id or kwargs.get("transit_id_id")
        self.model_year = model_year
        self.color = color
        self.load_capacity_kg = load_capacity_kg
        self.empty_weight_kg = empty_weight_kg
        self.motorcycle_capacity = motorcycle_capacity
        self.vin = vin
        self.fuel_type = fuel_type
        self.license_category = license_category
        self.transmission = transmission
        self.plate_transit_free = plate_transit_free
        self.owner_id = owner_id or kwargs.get("owner_id_id")
        self.holder_id = holder_id or kwargs.get("holder_id_id")
        self.default_driver_id = default_driver_id or kwargs.get("default_driver_id_id")
        self.is_available = is_available
