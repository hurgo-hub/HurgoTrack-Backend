from typing import Optional

from apps.core.entity import E_audit_base


class E_partner(E_audit_base):

    def __init__(
        self,
        company_id: Optional[int | dict] = None,
        name: Optional[str] = None,
        is_company: Optional[bool] = False,
        document_type: Optional[str] = 'CC',
        document_number: Optional[str] = None,
        email: Optional[str] = '',
        phone: Optional[str] = '',
        address: Optional[str] = '',
        location_id: Optional[int | dict] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.company_id = company_id or kwargs.get("company_id_id")
        self.name = name
        self.is_company = is_company
        self.document_type = document_type
        self.document_number = document_number
        self.email = email
        self.phone = phone
        self.address = address
        self.location_id = location_id or kwargs.get("location_id_id")
