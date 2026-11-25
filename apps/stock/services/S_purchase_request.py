"""Solicitudes de compra (Hurgo -> facturador de la empresa) y su enlace con las compras de Odoo.

1. Hurgo crea la solicitud (productos + cantidades, normalmente lo que da ``stock.requirements``)
   y se notifica a los facturadores de la empresa.
2. El facturador compra en Odoo y registra la referencia P000XX (``link_purchase``).
3. Se traen de Odoo las líneas de la compra y lo comprado entra al stock de la empresa.
   Cada línea de Odoo suma una sola vez: al re-sincronizar solo entra la diferencia.
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.models import M_company, M_user_company
from enginedj.base.services import BaseService
from enginedj.base.services.permissions import has_perm, require_perm, user_company_ids

from apps.orders.models import M_item, M_order_line
from apps.stock.entity import E_purchase_request
from apps.stock.models import M_purchase_request_line
from apps.stock.repository import R_purchase_request
from apps.stock.services.S_stock import S_stock, _dec

BILLER_GROUP = "facturador"


class S_purchase_request(BaseService[E_purchase_request]):

    def __init__(self):
        super().__init__(repository=R_purchase_request(), entity_class=E_purchase_request)
        self.repository: R_purchase_request = self.repository

    # ------------------------------------------------------------------
    # Alcance
    # ------------------------------------------------------------------
    def scope_company_ids(self, user):
        return None if has_perm(user, "stock.view_all_purchase_request") else user_company_ids(user)

    def _lock(self, user, request_id):
        request = self.repository.get_for_update(request_id)
        scope = self.scope_company_ids(user)
        if request is None or (scope is not None and request.company_id_id not in scope):
            raise BusinessNotFound("La solicitud de compra no existe.")
        return request

    @staticmethod
    def _require_state(request, states, action):
        if request.state not in states:
            raise BusinessError(
                f"No se puede {action}: la solicitud {request.code} está '{request.get_state_display()}'.",
                code="invalid_state",
            )

    # ------------------------------------------------------------------
    # 1. Crear y enviar
    # ------------------------------------------------------------------
    @transaction.atomic
    def create(self, user, *, company_id, lines, notes="", send=True):
        """lines: [{"item_id", "qty", "order_line_id"?}]."""
        require_perm(user, "stock.manage_purchase_request", "Solo el equipo de despacho pide compras.")
        company = M_company.objects.filter(pk=company_id, is_active=True).first()
        if company is None:
            raise BusinessNotFound("La empresa no existe.")
        if not lines:
            raise BusinessError("La solicitud debe tener al menos un producto.", code="empty_request")

        items = {i.pk: i for i in M_item.objects.filter(pk__in={int(l["item_id"]) for l in lines}, company_id=company,
                                                        is_active=True).select_related("type_item_id")}
        order_line_ids = {int(l["order_line_id"]) for l in lines if l.get("order_line_id")}
        order_lines = {ol.pk: ol for ol in M_order_line.objects.filter(pk__in=order_line_ids,
                                                                        order_id__company_id=company)}
        request = self.repository.create_request(company_id=company, state="draft", notes=notes or "",
                                                 create_user=user)
        rows = []
        for line in lines:
            item = items.get(int(line["item_id"]))
            if item is None:
                raise BusinessError(f"El producto {line['item_id']} no existe o es de otra empresa.", code="invalid_item")
            if not item.type_item_id.uses_stock:
                raise BusinessError(f"{item} no se maneja con stock; su compra va en el pedido.", code="no_stock_item")
            qty = _dec(line["qty"])
            if qty <= 0:
                raise BusinessError(f"La cantidad de {item} debe ser mayor que cero.")
            order_line = None
            if line.get("order_line_id"):
                order_line = order_lines.get(int(line["order_line_id"]))
                if order_line is None or order_line.item_id_id != item.pk:
                    raise BusinessError(f"La línea de pedido {line['order_line_id']} no es de {item}.",
                                        code="order_line_mismatch")
            rows.append(M_purchase_request_line(purchase_request_id=request, item_id=item, qty=qty,
                                                order_line_id=order_line, create_user=user))
        self.repository.add_lines(rows)
        if send:
            self._send(request, user)
        return request

    @transaction.atomic
    def send(self, user, request_id):
        require_perm(user, "stock.manage_purchase_request", "Solo el equipo de despacho pide compras.")
        request = self._lock(user, request_id)
        self._require_state(request, ("draft",), "enviar")
        self._send(request, user)
        return request

    def _send(self, request, user):
        self.repository.save_request(request, user, state="sent", sent_date=timezone.now())
        self._notify_billers(request, user)

    @staticmethod
    def _notify_billers(request, user):
        """Avisa a los facturadores de la empresa (usuarios del grupo ``facturador`` vinculados a ella)."""
        from enginedj.notification.models import M_notification

        group = Group.objects.filter(name=BILLER_GROUP).first()
        if group is None or user is None:
            return
        billers = (
            M_user_company.objects.filter(company_id=request.company_id, user_id__groups=group, user_id__is_active=True)
            .values_list("user_id", flat=True)
            .distinct()
        )
        lines = ", ".join(
            f"{line.item_id.name} x {line.qty.normalize():f}"
            for line in request.purchase_request_line_purchase_request_id.select_related("item_id")
        )
        for user_id in billers:
            M_notification.objects.create(
                user_from_id=user, user_to_id_id=user_id, is_user=True, type="info",
                title=f"Solicitud de compra {request.code}",
                message=f"Hurgo solicita comprar: {lines}. Registra la compra de Odoo cuando la hagas.",
            )

    @transaction.atomic
    def cancel(self, user, request_id, reason):
        require_perm(user, "stock.manage_purchase_request", "Solo el equipo de despacho cancela solicitudes.")
        request = self._lock(user, request_id)
        self._require_state(request, ("draft", "sent"), "cancelar")
        if not (reason or "").strip():
            raise BusinessError("Indica el motivo de la cancelación.")
        notes = f"{request.notes}\nCancelada: {reason.strip()}".strip()
        return self.repository.save_request(request, user, state="cancelled", notes=notes)

    # ------------------------------------------------------------------
    # 2-3. Compra en Odoo -> stock
    # ------------------------------------------------------------------
    @transaction.atomic
    def link_purchase(self, user, request_id, odoo_name):
        """El facturador (o despacho) registra la compra de Odoo; lo comprado entra al stock.

        Devuelve (solicitud, resumen) con lo que entró y las líneas de Odoo sin producto emparejado.
        """
        if not (has_perm(user, "stock.link_purchase_request") or has_perm(user, "stock.manage_purchase_request")):
            raise BusinessPermissionError("Solo el facturador o despacho registran la compra.")
        request = self._lock(user, request_id)
        self._require_state(request, ("sent", "purchased"), "registrar la compra")
        odoo_name = (odoo_name or "").strip()
        if not odoo_name:
            raise BusinessError("Indica la referencia de la compra en Odoo (ej. P00012).", code="odoo_required")
        if not settings.ODOO_ENABLED:
            raise BusinessError("La integración con Odoo está apagada (ODOO_ENABLED).", code="odoo_disabled")

        from apps.apiOdoo.services import S_odoo_purchase

        s_purchase = S_odoo_purchase()
        purchase = s_purchase.require_confirmed(s_purchase.sync_by_name(odoo_name, user, with_lines=True))
        summary = self.stock_purchase(purchase, request, user)
        request.odoo_purchases.add(purchase)
        fields = {"state": "purchased"}
        if request.purchased_date is None:
            fields["purchased_date"] = timezone.now()
        self.repository.save_request(request, user, **fields)
        return request, summary

    def stock_purchase(self, purchase, request, user) -> dict:
        """Suma al stock de la empresa cada línea de la compra (solo la diferencia aún no sumada)."""
        s_stock = S_stock()
        company_id = request.company_id_id
        refs = {str(line.product_odoo_id) for line in purchase.odoo_purchase_line_purchase_id.all() if line.product_odoo_id}
        items = {i.odoo_ref: i for i in M_item.objects.filter(company_id=company_id, odoo_ref__in=refs, is_active=True)}

        from apps.apiOdoo.repository import R_odoo_purchase

        stocked, unmatched = [], []
        for line in R_odoo_purchase().lines_for_update(purchase):
            item = items.get(str(line.product_odoo_id))
            if item is None:
                unmatched.append({"odoo_line_id": line.odoo_line_id, "product": line.product_name,
                                  "qty": line.product_qty})
                continue
            if line.item_id_id != item.pk:
                line.item_id = item
            diff = line.product_qty - line.qty_stocked
            if diff != 0:
                s_stock.add(company_id, item.pk, diff, "purchase_in", user, odoo_purchase_line_id=line,
                            purchase_request_id=request, description=f"Compra {purchase.name}")
                line.qty_stocked = line.product_qty
                stocked.append({"item_id": item.pk, "item": item.name, "qty": diff})
            line.update_user = user
            line.save()
        return {"purchase": purchase.name, "stocked": stocked, "unmatched": unmatched}

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def _require_view(self, user):
        if not (has_perm(user, "stock.view_m_purchase_request") or has_perm(user, "stock.link_purchase_request")):
            raise BusinessPermissionError("No tienes permiso para ver solicitudes de compra.")

    def detail(self, user, request_id):
        self._require_view(user)
        request = self.repository.with_detail(self.repository.visible(self.scope_company_ids(user))).filter(
            pk=request_id).first()
        if request is None:
            raise BusinessNotFound("La solicitud de compra no existe.")
        return request

    def list_scoped(self, user, *, company_id=None, state=None):
        self._require_view(user)
        qs = self.repository.with_detail(self.repository.visible(self.scope_company_ids(user)))
        if company_id:
            qs = qs.filter(company_id=company_id)
        if state:
            qs = qs.filter(state=state)
        return list(qs.order_by("-id")[:200])
