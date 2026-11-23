from enginedj.base.services import BaseService

from apps.core.permissions import require_perm
from apps.orders.entity import E_order_line
from apps.orders.repository import R_order_line


class S_order_line(BaseService[E_order_line]):

    def __init__(self):
        super().__init__(repository=R_order_line(), entity_class=E_order_line)
        self.repository: R_order_line = self.repository

    def refresh(self, line_ids, user):
        """Recalcula cantidades desde las asignaciones a viajes y el estado de los pedidos afectados."""
        from apps.orders.services.S_order import S_order

        line_ids = set(line_ids)
        if not line_ids:
            return
        order_ids = self.repository.recalculate(line_ids, user)
        S_order().apply_logistic_state(order_ids, user)

    def pending_for_trips(self, user, company_id=None):
        require_perm(user, "trips.build_trip", "Solo el equipo de despacho arma viajes.")
        return self.repository.pending_for_trips(company_id=company_id)
