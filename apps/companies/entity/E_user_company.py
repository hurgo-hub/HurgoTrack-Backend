from typing import Optional

from apps.core.entity import E_audit_base


class E_user_company(E_audit_base):

    def __init__(
        self,
        user_id: Optional[int | dict] = None,
        company_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.user_id = user_id or kwargs.get("user_id_id")
        self.company_id = company_id or kwargs.get("company_id_id")
