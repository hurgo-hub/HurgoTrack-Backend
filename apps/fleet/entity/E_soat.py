from datetime import date
from typing import Optional

from apps.core.entity import E_audit_base


class E_soat(E_audit_base):

    def __init__(
        self,
        vehicle_id: Optional[int | dict] = None,
        insurer_name: Optional[str] = None,
        policy_number: Optional[str] = None,
        date_start: Optional[date] = None,
        date_expire: Optional[date] = None,
        file: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.vehicle_id = vehicle_id or kwargs.get("vehicle_id_id")
        self.insurer_name = insurer_name
        self.policy_number = policy_number
        self.date_start = date_start
        self.date_expire = date_expire
        self.file = file
