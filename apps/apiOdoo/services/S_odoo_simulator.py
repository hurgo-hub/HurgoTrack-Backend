"""Simulador de compras de Odoo (solo con ``ODOO_SIMULATED=True``).

"Simular compra en Odoo" hace lo que haría el facturador en Odoo: crea la compra confirmada con los
productos y cantidades de la solicitud de compra (o del pedido). Queda con referencia ``SIM-<código>``
en el Odoo simulado; luego se registra con el flujo normal ("Registrar compra de Odoo") y lo comprado
entra al stock igual que con una compra real.
"""

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.models import M_company
from enginedj.base.services.permissions import has_perm

from apps.apiOdoo.models import M_odoo_purchase, M_odoo_purchase_line

FIRST_ID = 900_000_000  # ids del simulador, lejos de los de un Odoo real


class S_odoo_simulator:

    @staticmethod
    def require_on():
        if not settings.ODOO_SIMULATED:
            raise BusinessError("El simulador de Odoo está apagado (ODOO_SIMULATED=False en el .env).",
                                code="odoo_simulator_off")

    @transaction.atomic
    def create_purchase(self, user, company_id, *, purchase_request_id=None, order_id=None) -> M_odoo_purchase:
        self.require_on()
        if not (has_perm(user, "stock.link_purchase_request") or has_perm(user, "orders.confirm_order")):
            raise BusinessPermissionError("Solo el facturador o despacho registran compras.")
        company = M_company.objects.get(pk=company_id)
        code, lines = self._source(company, purchase_request_id, order_id)
        if purchase_request_id:
            missing = sorted({item.name for item, _ in lines if not (item.odoo_ref or "").isdigit()})
            if missing:
                raise BusinessError("Para simular la compra, ponle la Ref. Odoo (un número) a estos productos en "
                                    f"Mi empresa: {', '.join(missing)}.", code="odoo_ref_required")
        name = self._free_name(f"SIM-{code}")
        next_id = max(M_odoo_purchase.objects.aggregate(m=Max("odoo_id"))["m"] or 0, FIRST_ID) + 1
        next_line = max(M_odoo_purchase_line.objects.aggregate(m=Max("odoo_line_id"))["m"] or 0, FIRST_ID) + 1
        purchase = M_odoo_purchase.objects.create(
            odoo_id=next_id, name=name, partner_name=company.name, state="purchase", date_order=timezone.now(),
            amount_total=0, raw={"simulated": True}, synced_date=timezone.now(), create_user=user,
        )
        for n, (item, qty) in enumerate(lines):
            ref = item.odoo_ref if (item.odoo_ref or "").isdigit() else None
            M_odoo_purchase_line.objects.create(
                purchase_id=purchase, odoo_line_id=next_line + n, product_odoo_id=int(ref) if ref else None,
                product_name=item.name, product_qty=qty, qty_received=qty, uom_name=item.unit or "",
                raw={"simulated": True}, create_user=user,
            )
        return purchase

    @staticmethod
    def _source(company, purchase_request_id, order_id):
        if purchase_request_id:
            from apps.stock.models import M_purchase_request

            request = M_purchase_request.objects.filter(pk=purchase_request_id, company_id=company).first()
            if request is None:
                raise BusinessNotFound("La solicitud de compra no existe.")
            if request.state not in ("sent", "purchased"):
                raise BusinessError(f"La solicitud {request.code} está '{request.get_state_display()}': no se compra.",
                                    code="invalid_state")
            rows = request.purchase_request_line_purchase_request_id.filter(is_active=True).select_related("item_id")
            return request.code, [(line.item_id, line.qty) for line in rows]
        if order_id:
            from apps.orders.models import M_order

            order = M_order.objects.filter(pk=order_id, company_id=company).first()
            if order is None:
                raise BusinessNotFound("El pedido no existe.")
            rows = order.order_line_order_id.filter(is_active=True).select_related("item_id")
            return order.code, [(line.item_id, line.qty) for line in rows]
        raise BusinessError("Indica la solicitud de compra o el pedido.", code="invalid_input")

    @staticmethod
    def _free_name(base):
        name, n = base, 1
        while M_odoo_purchase.objects.filter(name=name).exists():
            n += 1
            name = f"{base}-{n}"
        return name
