from decimal import Decimal

from django.db.models import Sum

from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.orders.entity import E_order_line
from apps.orders.models import M_order_line, M_order_line_trip


class R_order_line(InvalidateAppsMixin, BaseRepositoryImpl[E_order_line]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_order_line, entity_class=E_order_line)
        self.model: M_order_line = self.model

    def lock_active(self, line_ids) -> set[int]:
        """Bloquea las líneas (FOR UPDATE) y devuelve los ids que existen."""
        return set(
            self.model.objects.select_for_update().filter(pk__in=line_ids, is_active=True).values_list("pk", flat=True)
        )

    def with_order_and_item(self, line_ids) -> list[M_order_line]:
        return list(
            self.model.objects.filter(pk__in=line_ids).select_related("order_id", "item_id").order_by("pk")
        )

    def replace_lines(self, order, rows: list[M_order_line]):
        """Reemplaza las líneas de un pedido sin confirmar (no tienen asignaciones a viajes)."""
        self.model.objects.filter(order_id=order).delete()
        self.model.objects.bulk_create(rows)
        self._invalidate_list_cache()

    def has_quantities_in_trips(self, order) -> bool:
        lines = self.model.objects.filter(order_id=order)
        return lines.filter(qty_assigned__gt=0).exists() or lines.filter(qty_delivered__gt=0).exists()

    def cancel_all(self, order, user):
        from django.utils import timezone

        self.model.objects.filter(order_id=order).exclude(state="cancelled").update(
            state="cancelled", update_user=user, update_date=timezone.now()
        )
        self._invalidate_list_cache()

    def recalculate(self, line_ids, user) -> set[int]:
        """Recalcula asignado / entregado desde las asignaciones y devuelve los pedidos afectados.

        No cuentan las asignaciones de viajes cancelados ni las de paradas devueltas.
        """
        order_ids = set()
        for line in self.model.objects.select_for_update().filter(pk__in=line_ids):
            valid = (
                M_order_line_trip.objects.filter(order_line_id=line, is_active=True)
                .exclude(trip_line_id__trip_id__state="cancelled")
                .exclude(trip_line_id__state="returned")
            )
            line.qty_assigned = valid.aggregate(s=Sum("qty"))["s"] or Decimal("0")
            line.qty_delivered = valid.filter(trip_line_id__state="delivered").aggregate(s=Sum("qty"))["s"] or Decimal("0")
            if line.state != "cancelled":
                if line.qty_delivered >= line.qty:
                    line.state = "delivered"
                elif line.qty_assigned >= line.qty:
                    line.state = "assigned"
                elif line.qty_assigned > 0:
                    line.state = "partial"
                else:
                    line.state = "pending"
            line.update_user = user
            line.save()
            order_ids.add(line.order_id_id)
        self._invalidate_list_cache()
        return order_ids

    def order_state_from_lines(self, order) -> str:
        """Estado logístico del pedido según sus líneas activas."""
        lines = self.model.objects.filter(order_id=order, is_active=True).exclude(state="cancelled")
        if lines.exists() and not lines.exclude(state="delivered").exists():
            return "delivered"
        if lines.filter(qty_assigned__gt=0).exists():
            return "in_progress"
        return "confirmed"

    def pending_for_trips(self, company_id=None, limit: int = 200) -> list[M_order_line]:
        """Líneas de pedidos confirmados con cantidad por asignar a viajes."""
        qs = (
            self.model.objects.filter(
                is_active=True,
                order_id__is_active=True,
                order_id__state__in=["confirmed", "in_progress"],
                state__in=["pending", "partial"],
            )
            .select_related("order_id", "recipient_id", "address_id", "item_id__brand_id")
            .order_by("order_id__order_date", "order_id", "id")
        )
        if company_id:
            qs = qs.filter(order_id__company_id=company_id)
        return list(qs[:limit])
