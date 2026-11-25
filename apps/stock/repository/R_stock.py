from decimal import Decimal

from django.db.models import F, Q, Sum

from enginedj.base.cache import InvalidateAppsMixin
from enginedj.base.repository import BaseRepositoryImpl

from apps.stock.entity import E_stock, E_stock_move
from apps.stock.models import M_purchase_request_line, M_stock, M_stock_move


class R_stock(InvalidateAppsMixin, BaseRepositoryImpl[E_stock]):
    invalidate_app_labels = ("stock",)

    def __init__(self):
        super().__init__(model=M_stock, entity_class=E_stock)
        self.model: M_stock = self.model

    def lock(self, company_id, item_id) -> M_stock:
        """Fila de stock bloqueada (FOR UPDATE); la crea en cero si no existe."""
        self.model.objects.get_or_create(company_id_id=company_id, item_id_id=item_id)
        return self.model.objects.select_for_update().get(company_id_id=company_id, item_id_id=item_id)

    def move(self, stock: M_stock, qty: Decimal, move_type: str, user, **links) -> M_stock_move:
        stock.qty_available += qty
        stock.update_user = user
        stock.save()
        move = M_stock_move.objects.create(
            company_id_id=stock.company_id_id, item_id_id=stock.item_id_id, move_type=move_type, qty=qty,
            balance=stock.qty_available, create_user=user, **links,
        )
        self._invalidate_list_cache()
        return move

    def available_by_item(self, company_id, item_ids=None) -> dict[int, Decimal]:
        qs = self.model.objects.filter(company_id=company_id)
        if item_ids is not None:
            qs = qs.filter(item_id__in=item_ids)
        return dict(qs.values_list("item_id", "qty_available"))

    def visible(self, company_ids=None, company_id=None, only_available=False):
        qs = self.model.objects.select_related("company_id", "item_id").order_by("company_id__name", "item_id__name")
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        if company_id:
            qs = qs.filter(company_id=company_id)
        if only_available:
            qs = qs.filter(qty_available__gt=0)
        return list(qs)

    def moves(self, company_ids=None, company_id=None, item_id=None, limit=200) -> list[M_stock_move]:
        qs = M_stock_move.objects.select_related(
            "item_id", "create_user", "odoo_purchase_line_id__purchase_id", "purchase_request_id",
            "order_line_trip_id__trip_line_id__trip_id", "order_line_trip_id__order_line_id__order_id",
        )
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        if company_id:
            qs = qs.filter(company_id=company_id)
        if item_id:
            qs = qs.filter(item_id=item_id)
        return list(qs.order_by("-move_date", "-id")[:limit])

    def moves_of_allocation(self, allocation_id) -> Decimal:
        """Neto de stock de un cargue (negativo = sigue cargado)."""
        return M_stock_move.objects.filter(order_line_trip_id=allocation_id).aggregate(s=Sum("qty"))["s"] or Decimal("0")

    @staticmethod
    def requested_not_bought(company_id) -> dict[int, Decimal]:
        """Cantidad en solicitudes enviadas que el facturador aún no compra, por producto."""
        rows = (
            M_purchase_request_line.objects.filter(
                is_active=True, purchase_request_id__company_id=company_id, purchase_request_id__state="sent",
                purchase_request_id__is_active=True,
            )
            .values("item_id")
            .annotate(s=Sum("qty"))
        )
        return {row["item_id"]: row["s"] for row in rows}

    @staticmethod
    def pending_demand(company_id) -> dict[int, Decimal]:
        """Lo que falta por cargar de los pedidos abiertos (productos con stock), por producto."""
        from apps.orders.models import M_order_line

        rows = (
            M_order_line.objects.filter(
                is_active=True, order_id__is_active=True, order_id__company_id=company_id,
                order_id__state__in=["requested", "confirmed", "in_progress"],
                state__in=["pending", "partial"], item_id__type_item_id__uses_stock=True,
            )
            .values("item_id")
            .annotate(s=Sum(F("qty") - F("qty_assigned")))
        )
        return {row["item_id"]: row["s"] for row in rows if row["s"] and row["s"] > 0}
