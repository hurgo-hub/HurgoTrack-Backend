from enginedj.base.services import BaseService

from apps.companies.entity import E_company
from apps.companies.repository import R_company
from apps.core.exceptions import BusinessPermissionError
from apps.core.permissions import has_perm


class S_company(BaseService[E_company]):

    def __init__(self):
        super().__init__(repository=R_company(), entity_class=E_company)
        self.repository: R_company = self.repository

    def recipients(self, user, query: str = ""):
        """Destinatarios con direcciones, para armar pedidos."""
        if not (has_perm(user, "orders.add_m_order") or has_perm(user, "trips.build_trip")):
            raise BusinessPermissionError("Solo comerciales y despacho consultan destinatarios.")
        return self.repository.recipients((query or "").strip())
