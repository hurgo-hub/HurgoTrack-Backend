from enginedj.base.exceptions import BusinessPermissionError
from enginedj.base.services import BaseService
from enginedj.base.services.permissions import has_perm

from apps.locations.entity import E_address
from apps.locations.repository import R_address


class S_address(BaseService[E_address]):

    def __init__(self):
        super().__init__(repository=R_address(), entity_class=E_address)
        self.repository: R_address = self.repository

    def recipients(self, user, query: str = ""):
        """Destinatarios con sus direcciones, para armar pedidos."""
        if not (has_perm(user, "orders.add_m_order") or has_perm(user, "trips.build_trip")):
            raise BusinessPermissionError("Solo comerciales y despacho consultan destinatarios.")
        return self.repository.recipients((query or "").strip())
