from typing import Optional

from apps.core.entity import E_audit_base


class E_brand(E_audit_base):

    def __init__(
        self,
        name: Optional[str] = None,
        company_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.company_id = company_id or kwargs.get("company_id_id")
