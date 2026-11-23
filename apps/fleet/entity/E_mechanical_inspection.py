from datetime import date
from typing import Optional

from apps.core.entity import E_audit_base


class E_mechanical_inspection(E_audit_base):

    def __init__(
        self,
        vehicle_id: Optional[int | dict] = None,
        certificate_number: Optional[str] = None,
        cda_name: Optional[str] = None,
        date_expedition: Optional[date] = None,
        date_expire: Optional[date] = None,
        file: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.vehicle_id = vehicle_id or kwargs.get("vehicle_id_id")
        self.certificate_number = certificate_number
        self.cda_name = cda_name
        self.date_expedition = date_expedition
        self.date_expire = date_expire
        self.file = file
