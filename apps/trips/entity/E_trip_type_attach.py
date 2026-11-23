from typing import Optional

from apps.core.entity import E_audit_base


class E_trip_type_attach(E_audit_base):

    def __init__(
        self,
        name: Optional[str] = None,
        key: Optional[str] = None,
        is_delivery_proof: Optional[bool] = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.key = key
        self.is_delivery_proof = is_delivery_proof
