from typing import Optional

from apps.core.entity import E_audit_base


class E_company(E_audit_base):

    def __init__(
        self,
        name: Optional[str] = None,
        document_type: Optional[str] = 'NIT',
        document_number: Optional[str] = None,
        verification_digit: Optional[str] = '',
        email: Optional[str] = '',
        phone: Optional[str] = '',
        logo: Optional[str] = None,
        color: Optional[str] = '',
        header: Optional[str] = '',
        footer: Optional[str] = '',
        slogan: Optional[str] = '',
        is_client: Optional[bool] = False,
        is_carrier: Optional[bool] = False,
        is_freelance: Optional[bool] = False,
        is_recipient: Optional[bool] = False,
        odoo_ref: Optional[str] = '',
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.name = name
        self.document_type = document_type
        self.document_number = document_number
        self.verification_digit = verification_digit
        self.email = email
        self.phone = phone
        self.logo = logo
        self.color = color
        self.header = header
        self.footer = footer
        self.slogan = slogan
        self.is_client = is_client
        self.is_carrier = is_carrier
        self.is_freelance = is_freelance
        self.is_recipient = is_recipient
        self.odoo_ref = odoo_ref
