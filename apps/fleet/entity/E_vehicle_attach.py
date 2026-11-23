from datetime import date
from typing import Optional

from enginedj.base.entity import E_model_base


class E_vehicle_attach(E_model_base):

    def __init__(
        self,
        vehicle_id: Optional[int | dict] = None,
        name: Optional[str] = None,
        file: Optional[str] = None,
        date_expire: Optional[date] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.vehicle_id = vehicle_id or kwargs.get("vehicle_id_id")
        self.name = name
        self.file = file
        self.date_expire = date_expire
