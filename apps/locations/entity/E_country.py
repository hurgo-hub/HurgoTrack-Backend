from typing import Optional

from apps.core.entity import E_audit_base


class E_country(E_audit_base):

    def __init__(
        self,
        iso_code: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.iso_code = iso_code
        self.name = name
