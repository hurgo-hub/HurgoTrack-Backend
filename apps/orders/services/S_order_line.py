from enginedj.base.services import BaseService

from enginedj.base.services.permissions import require_perm
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
        """Líneas por asignar; las de productos con stock traen ``stock_available`` (lo ve solo Hurgo)."""
        from apps.stock.repository import R_stock

        require_perm(user, "trips.build_trip", "Solo el equipo de despacho arma viajes.")
        lines = self.repository.pending_for_trips(company_id=company_id)
        r_stock, cache = R_stock(), {}
        for line in lines:
            if not line.item_id.type_item_id.uses_stock:
                line.stock_available = None
                continue
            company = line.order_id.company_id_id
            if company not in cache:
                cache[company] = r_stock.available_by_item(company)
            line.stock_available = cache[company].get(line.item_id_id, 0)
        return lines
