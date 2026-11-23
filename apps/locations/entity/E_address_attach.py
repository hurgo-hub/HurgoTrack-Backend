from typing import Optional

from apps.core.entity import E_audit_base


class E_address_attach(E_audit_base):

    def __init__(
        self,
        address_id: Optional[int | dict] = None,
        name: Optional[str] = '',
        file: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.address_id = address_id or kwargs.get("address_id_id")
        self.name = name
        self.file = file
