from typing import Optional

from apps.core.entity import E_audit_base


class E_vehicle_gps(E_audit_base):

    def __init__(
        self,
        vehicle_id: Optional[int | dict] = None,
        operator: Optional[str] = None,
        username: Optional[str] = '',
        password: Optional[str] = '',
        api_key: Optional[str] = '',
        api_secret: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.vehicle_id = vehicle_id or kwargs.get("vehicle_id_id")
        self.operator = operator
        self.username = username
        self.password = password
        self.api_key = api_key
        self.api_secret = api_secret
