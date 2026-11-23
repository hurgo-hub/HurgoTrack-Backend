"""Reglas de pedidos (pasos 1 y 2 del documento).

1. Pedido        -> create / update / submit   (comercial de la empresa cliente)
2. Confirmación  -> confirm (compra en Odoo)   (despacho)
   Cancelación   -> cancel

"En despacho" y "entregado" los mueve ``apply_logistic_state``, que llama el
servicio de líneas cuando cambian las asignaciones a viajes.
"""

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from enginedj.base.services import BaseService

from apps.companies.repository import R_company
from apps.core.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from apps.core.permissions import has_perm, require_perm, user_company_ids
from apps.locations.repository import R_address
from apps.orders.entity import E_order
from apps.orders.models import M_order_line
from apps.orders.repository import R_item, R_order, R_order_event, R_order_line

EDITABLE_STATES = ("draft", "requested")
LOGISTIC_STATES = ("confirmed", "in_progress", "delivered")
STATE_EVENT_NAMES = {
    "confirmed": "Pedido sin viajes asignados",
    "in_progress": "Pedido en despacho",
    "delivered": "Pedido entregado",
}


class S_order(BaseService[E_order]):

    def __init__(self):
        super().__init__(repository=R_order(), entity_class=E_order)
        self.repository: R_order = self.repository
        self.r_line = R_order_line()
        self.r_event = R_order_event()
        self.r_item = R_item()
        self.r_company = R_company()
        self.r_address = R_address()

    # ------------------------------------------------------------------
    # Permisos y alcance
    # ------------------------------------------------------------------
    def scope_company_ids(self, user):
        """None = todas las empresas; si no, las empresas del usuario."""
        return None if has_perm(user, "orders.view_all_order") else user_company_ids(user)

    def can_manage_company(self, user, company_id) -> bool:
        if has_perm(user, "orders.create_any_company_order"):
            return True
        return has_perm(user, "orders.add_m_order") and company_id in user_company_ids(user)

    def _require_manage(self, user, order):
        if not self.can_manage_company(user, order.company_id_id):
            raise BusinessPermissionError("No puedes modificar pedidos de esta empresa.")

    @staticmethod
    def _require_state(order, states, action):
        if order.state not in states:
            raise BusinessError(
                f"No se puede {action}: el pedido {order.code} está '{order.get_state_display()}'.",
                code="invalid_state",
            )

    def _lock(self, order_id):
        order = self.repository.get_for_update(order_id)
        if order is None:
            raise BusinessNotFound("El pedido no existe.")
        return order

    def _set_state(self, order, user, new_state, name, description="", **fields):
        old_state = self.repository.set_state(order, new_state, user, **fields)
        self.r_event.register(order, user, name, from_state=old_state, to_state=new_state, description=description)

    # ------------------------------------------------------------------
    # Validaciones de datos
    # ------------------------------------------------------------------
    def _resolve_company(self, user, company_id):
        if company_id is None:
            companies = user_company_ids(user)
            if len(companies) != 1:
                raise BusinessError("Indica la empresa del pedido.", code="company_required")
            company_id = companies[0]
        if not self.can_manage_company(user, company_id):
            raise BusinessPermissionError("No puedes crear pedidos para esa empresa.")
        company = self.r_company.get_active(company_id)
        if company is None:
            raise BusinessNotFound("La empresa no existe.")
        if not company.is_client:
            raise BusinessError(f"{company} no está registrada como empresa cliente.", code="not_client")
        return company

    def _resolve_origin(self, company, address_id):
        address = self.r_address.get_active(address_id)
        if address is None:
            raise BusinessNotFound("La dirección de cargue no existe.")
        if address.company_id_id != company.pk:
            raise BusinessError("La dirección de cargue no pertenece a la empresa del pedido.", code="address_mismatch")
        return address

    def _build_lines(self, order, user, lines) -> list[M_order_line]:
        if not lines:
            raise BusinessError("El pedido debe tener al menos un producto.", code="empty_order")
        items = self.r_item.active_by_ids({int(line["item_id"]) for line in lines}, order.company_id_id)
        seen, rows = set(), []
        for line in lines:
            item = items.get(int(line["item_id"]))
            if item is None:
                raise BusinessError(f"El producto {line['item_id']} no existe o es de otra empresa.",
                                    code="invalid_item")
            recipient = self.r_company.get_active(line["recipient_id"])
            if recipient is None:
                raise BusinessNotFound(f"El destinatario {line['recipient_id']} no existe.")
            address = self.r_address.get_active(line["address_id"])
            if address is None:
                raise BusinessNotFound(f"La dirección {line['address_id']} no existe.")
            if address.company_id_id != recipient.pk:
                raise BusinessError(f"La dirección '{address.name}' no pertenece a {recipient}.", code="address_mismatch")
            key = (item.pk, address.pk)
            if key in seen:
                raise BusinessError(f"{item} está repetido para la misma dirección; suma las cantidades.",
                                    code="duplicate_item")
            seen.add(key)
            qty = line["qty"] if isinstance(line["qty"], Decimal) else Decimal(str(line["qty"]))
            if qty <= 0:
                raise BusinessError(f"La cantidad de {item} debe ser mayor que cero.")
            if item.is_serialized and qty != qty.to_integral_value():
                raise BusinessError(f"{item} se pide por unidades enteras.", code="integer_qty")
            rows.append(M_order_line(order_id=order, item_id=item, recipient_id=recipient, address_id=address,
                                     qty=qty, create_user_id=user))
        return rows

    # ------------------------------------------------------------------
    # 1. Pedido
    # ------------------------------------------------------------------
    @transaction.atomic
    def create(self, user, *, address_id, lines, company_id=None, order_date=None, notes="", submit=True):
        require_perm(user, "orders.add_m_order", "No tienes permiso para crear pedidos.")
        company = self._resolve_company(user, company_id)
        origin = self._resolve_origin(company, address_id)
        order = self.repository.create_order(
            company_id=company, address_id=origin, order_date=order_date or timezone.localdate(),
            notes=notes or "", state="draft", create_user_id=user,
        )
        self.r_event.register(order, user, "Pedido creado", to_state="draft")
        self.r_line.replace_lines(order, self._build_lines(order, user, lines))
        if submit:
            self._set_state(order, user, "requested", "Pedido enviado a Hurgo")
        return order

    @transaction.atomic
    def update(self, user, order_id, *, address_id, lines, order_date=None, notes=""):
        """Reemplaza dirección de cargue y productos mientras Hurgo no lo haya confirmado."""
        order = self._lock(order_id)
        self._require_manage(user, order)
        self._require_state(order, EDITABLE_STATES, "modificar")
        order.address_id = self._resolve_origin(order.company_id, address_id)
        order.order_date = order_date or order.order_date
        order.notes = notes or ""
        self.repository.save_order(order, user)
        self.r_line.replace_lines(order, self._build_lines(order, user, lines))
        self.r_event.register(order, user, "Pedido modificado")
        return order

    @transaction.atomic
    def submit(self, user, order_id):
        require_perm(user, "orders.submit_order", "No tienes permiso para enviar pedidos.")
        order = self._lock(order_id)
        self._require_manage(user, order)
        self._require_state(order, ("draft",), "enviar")
        self._set_state(order, user, "requested", "Pedido enviado a Hurgo")
        return order

    # ------------------------------------------------------------------
    # 2. Confirmación
    # ------------------------------------------------------------------
    @transaction.atomic
    def confirm(self, user, order_id, *, odoo_purchase):
        """Despacho confirma la compra en Odoo. Con ODOO_ENABLED se valida que exista y esté confirmada allá."""
        require_perm(user, "orders.confirm_order", "Solo el equipo de despacho confirma pedidos.")
        order = self._lock(order_id)
        self._require_state(order, ("requested",), "confirmar")
        odoo_purchase = (odoo_purchase or "").strip()
        if not odoo_purchase:
            raise BusinessError("Indica la referencia de la compra en Odoo.", code="odoo_required")
        if settings.ODOO_ENABLED:
            from apps.apiOdoo.services import S_odoo_purchase

            odoo_purchase = S_odoo_purchase().validate_for_order(odoo_purchase, order, user).name
        self._set_state(order, user, "confirmed", "Compra confirmada en Odoo", description=odoo_purchase,
                        odoo_purchase=odoo_purchase, confirmed_date=timezone.now())
        return order

    @transaction.atomic
    def cancel(self, user, order_id, reason):
        """Antes de confirmar: el comercial. Confirmado: despacho, si nada del pedido va en viajes."""
        order = self._lock(order_id)
        if not (reason or "").strip():
            raise BusinessError("Indica el motivo de la cancelación.")
        if order.state in EDITABLE_STATES:
            require_perm(user, "orders.cancel_order", "No tienes permiso para cancelar pedidos.")
            self._require_manage(user, order)
        elif order.state in ("confirmed", "in_progress"):
            require_perm(user, "orders.cancel_confirmed_order",
                         "Un pedido confirmado solo lo cancela el equipo de despacho.")
            if self.r_line.has_quantities_in_trips(order):
                raise BusinessError("El pedido tiene cantidades en viajes; cancela o termina esos viajes primero.",
                                    code="order_in_trips")
        else:
            self._require_state(order, (), "cancelar")
        self.r_line.cancel_all(order, user)
        self._set_state(order, user, "cancelled", "Pedido cancelado", description=reason)
        return order

    # ------------------------------------------------------------------
    # Estado logístico (lo mueven los viajes)
    # ------------------------------------------------------------------
    def apply_logistic_state(self, order_ids, user):
        for order_id in sorted(order_ids):
            order = self.repository.get_for_update(order_id)
            if order is None or order.state not in LOGISTIC_STATES:
                continue
            new_state = self.r_line.order_state_from_lines(order)
            if new_state == order.state:
                continue
            self._set_state(order, user, new_state, STATE_EVENT_NAMES[new_state])
            if new_state == "delivered" and settings.ODOO_ENABLED:
                from apps.apiOdoo.tasks import notify_order_delivered

                transaction.on_commit(lambda pk=order.pk: notify_order_delivered.delay(pk), robust=True)

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def detail(self, user, order_id):
        require_perm(user, "orders.view_m_order", "No tienes permiso para ver pedidos.")
        order = self.repository.with_detail(self.repository.visible(self.scope_company_ids(user))).filter(
            pk=order_id).first()
        if order is None:
            raise BusinessNotFound("El pedido no existe.")
        return order

    def list_scoped(self, user, data: dict):
        """Como ``list.relations`` del motor, limitado a las empresas que el usuario puede ver."""
        data = dict(data or {})
        company_ids = self.scope_company_ids(user)
        if company_ids is not None:
            data["filters"] = {**(data.get("filters") or {}), "company_id__in": company_ids}
        data.pop("user", None)
        return self.list_with_relations_m2m(user=user, **data)

    def items_lookup(self, user, company_id=None, query=""):
        require_perm(user, "orders.add_m_order", "No tienes permiso para consultar productos.")
        company_ids = None if has_perm(user, "orders.create_any_company_order") else user_company_ids(user)
        return self.r_item.lookup(company_ids=company_ids, company_id=company_id, query=(query or "").strip())
