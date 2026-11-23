from typing import Optional

from apps.core.entity import E_audit_base


class E_user_detail(E_audit_base):

    def __init__(
        self,
        user_id: Optional[int | dict] = None,
        document_type: Optional[str] = 'CC',
        document_number: Optional[str] = '',
        phone: Optional[str] = '',
        avatar: Optional[str] = None,
        default_company_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.user_id = user_id or kwargs.get("user_id_id")
        self.document_type = document_type
        self.document_number = document_number
        self.phone = phone
        self.avatar = avatar
        self.default_company_id = default_company_id or kwargs.get("default_company_id_id")
