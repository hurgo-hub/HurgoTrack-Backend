"""Stock de una empresa por producto (materiales de Distritodo).

- Entra por compras de Odoo (``add`` desde S_purchase_request.link_purchase).
- Sale al cargar una línea de pedido en un viaje (``take`` desde S_trip._allocate).
- Vuelve si el viaje se cancela o la parada se devuelve (``give_back_allocation``).
- ``requirements``: cuánto mandar a comprar = pendiente por cargar − disponible − ya solicitado.
"""

from decimal import Decimal

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.models import M_company
from enginedj.base.services import BaseService
from enginedj.base.services.permissions import has_perm, require_perm, user_company_ids

from apps.orders.models import M_item
from apps.stock.entity import E_stock
from apps.stock.repository import R_stock

ZERO = Decimal("0")


def _dec(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


class S_stock(BaseService[E_stock]):

    def __init__(self):
        super().__init__(repository=R_stock(), entity_class=E_stock)
        self.repository: R_stock = self.repository

    # ------------------------------------------------------------------
    # Alcance
    # ------------------------------------------------------------------
    def scope_company_ids(self, user):
        """None = todas (Hurgo); si no, las empresas del usuario (ej. el facturador de Distritodo)."""
        return None if has_perm(user, "stock.view_all_stock") else user_company_ids(user)

    def _require_view(self, user, company_id=None):
        require_perm(user, "stock.view_m_stock", "No tienes permiso para ver el stock.")
        scope = self.scope_company_ids(user)
        if company_id and scope is not None and company_id not in scope:
            raise BusinessPermissionError("No puedes ver el stock de esa empresa.")
        return scope

    # ------------------------------------------------------------------
    # Movimientos (los llaman otros servicios dentro de su transacción)
    # ------------------------------------------------------------------
    def add(self, company_id, item_id, qty, move_type, user, **links):
        qty = _dec(qty)
        if qty == 0:
            return None
        stock = self.repository.lock(company_id, item_id)
        if stock.qty_available + qty < 0:
            raise BusinessError(
                f"{stock.item_id}: el stock quedaría negativo ({stock.qty_available} + {qty}).", code="insufficient_stock"
            )
        return self.repository.move(stock, qty, move_type, user, **links)

    def take(self, company_id, item, qty, user, *, allocation=None, description=""):
        """Carga a un viaje: descuenta del stock; falla si no alcanza."""
        qty = _dec(qty)
        stock = self.repository.lock(company_id, item.pk)
        if qty > stock.qty_available:
            raise BusinessError(
                f"{item}: quieres cargar {qty} y solo hay {stock.qty_available} en stock. Lo que falte queda "
                "pendiente para otro viaje (o pide una compra).", code="insufficient_stock",
            )
        return self.repository.move(stock, -qty, "trip_out", user, order_line_trip_id=allocation,
                                    description=description)

    def give_back_allocation(self, allocation, move_type, user, description=""):
        """Devuelve al stock lo que un cargue (order_line_trip) tenga aún descontado."""
        item = allocation.order_line_id.item_id
        if not item.type_item_id.uses_stock:
            return None
        loaded = -self.repository.moves_of_allocation(allocation.pk)
        if loaded <= 0:
            return None
        company_id = allocation.order_line_id.order_id.company_id_id
        stock = self.repository.lock(company_id, item.pk)
        return self.repository.move(stock, loaded, move_type, user, order_line_trip_id=allocation,
                                    description=description)

    def adjust(self, user, *, company_id, item_id, qty, reason):
        require_perm(user, "stock.adjust_stock", "Solo administración ajusta el stock.")
        if not (reason or "").strip():
            raise BusinessError("Indica el motivo del ajuste.")
        item = M_item.objects.filter(pk=item_id, company_id=company_id, is_active=True).first()
        if item is None:
            raise BusinessNotFound("El producto no existe o es de otra empresa.")
        return self.add(company_id, item_id, qty, "adjust", user, description=reason.strip()[:255])

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def requirements(self, user, company_id):
        """Necesidad de compra por producto para los pedidos abiertos de la empresa.

        to_buy = pendiente por cargar − disponible − ya solicitado (sin comprar), nunca negativo.
        Ej.: pedido de 200 bolsas, 100 en stock, nada solicitado -> comprar 100.
        """
        self._require_view(user, company_id)
        if not M_company.objects.filter(pk=company_id, is_active=True).exists():
            raise BusinessNotFound("La empresa no existe.")
        demand = self.repository.pending_demand(company_id)
        requested = self.repository.requested_not_bought(company_id)
        available = self.repository.available_by_item(company_id)
        item_ids = set(demand) | set(requested) | {k for k, v in available.items() if v > 0}
        items = {i.pk: i for i in M_item.objects.filter(pk__in=item_ids).select_related("type_item_id")}
        rows = []
        for item_id in sorted(item_ids, key=lambda pk: items[pk].name):
            pending = demand.get(item_id, ZERO)
            stock = available.get(item_id, ZERO)
            in_requests = requested.get(item_id, ZERO)
            rows.append({
                "item_id": item_id,
                "item": items[item_id].name,
                "unit": items[item_id].unit,
                "pending": pending,
                "available": stock,
                "in_requests": in_requests,
                "to_buy": max(pending - stock - in_requests, ZERO),
            })
        return rows

    def list_stock(self, user, company_id=None, only_available=False):
        scope = self._require_view(user, company_id)
        return self.repository.visible(company_ids=scope, company_id=company_id, only_available=only_available)

    def list_moves(self, user, company_id=None, item_id=None):
        scope = self._require_view(user, company_id)
        return self.repository.moves(company_ids=scope, company_id=company_id, item_id=item_id)
