"""Steps de pedidos. Cada uno se expone como workflow: POST /api/workflows/sync/<nombre>/."""

from enginedj.modules.registry import register_module

from apps.companies.tenancy import in_company_schema

from enginedj.base.steps.helpers import context_user, results, validate_input
from apps.orders.serializers import (
    Sz_cancel_in,
    Sz_confirm_in,
    Sz_loading_point_in,
    Sz_order_detail,
    Sz_order_id_in,
    Sz_order_in,
    Sz_order_update_in,
)
from apps.orders.services import S_order


def _detail(user, order_id):
    return results(Sz_order_detail(S_order().detail(user, order_id)).data)


@register_module("orders.create", important=True)
@in_company_schema()
def create_order(context, params, execution):
    """Paso 1: el comercial crea el pedido. "submit": false lo deja en borrador."""
    user = context_user(context)
    data = validate_input(Sz_order_in, context)
    order = S_order().create(
        user, company_id=data.get("company_id"), address_id=data.get("address_id"), lines=data["lines"],
        order_date=data.get("order_date"), notes=data.get("notes", ""), submit=data.get("submit", True),
    )
    return _detail(user, order.pk)


@register_module("orders.update", important=True)
@in_company_schema()
def update_order(context, params, execution):
    """Reemplaza dirección de cargue y productos mientras no esté confirmado."""
    user = context_user(context)
    data = validate_input(Sz_order_update_in, context)
    S_order().update(user, data["order_id"], address_id=data.get("address_id"), lines=data["lines"],
                     order_date=data.get("order_date"), notes=data.get("notes", ""))
    return _detail(user, data["order_id"])


@register_module("orders.submit", important=True)
@in_company_schema()
def submit_order(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_order_id_in, context)
    S_order().submit(user, data["order_id"])
    return _detail(user, data["order_id"])


@register_module("orders.confirm", important=True)
@in_company_schema()
def confirm_order(context, params, execution):
    """Paso 2: despacho confirma la compra en Odoo."""
    user = context_user(context)
    data = validate_input(Sz_confirm_in, context)
    S_order().confirm(user, data["order_id"], odoo_purchase=data["odoo_purchase"],
                      loading_address_id=data.get("loading_address_id"))
    return _detail(user, data["order_id"])


@register_module("orders.cancel", important=True)
@in_company_schema()
def cancel_order(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_cancel_in, context)
    S_order().cancel(user, data["order_id"], data["reason"])
    return _detail(user, data["order_id"])


@register_module("orders.retrieve", important=True)
@in_company_schema()
def retrieve_order(context, params, execution):
    """Detalle con líneas, viajes en que va cada una e historial."""
    user = context_user(context)
    data = validate_input(Sz_order_id_in, context)
    return _detail(user, data["order_id"])


@register_module("orders.list", important=True)
@in_company_schema(optional=True)
def list_orders(context, params, execution):
    """Igual que list.relations (data: fields, relations, filters...). Usuario de empresa: los suyos.
    Hurgo: los de una empresa (company_id) o, sin company_id, los de todas (con ``company_id`` en cada fila)."""
    user = context_user(context)
    data = context.get("data") or {}
    if context.get("company_id") is None:
        return results(S_order().list_all_companies(user, data))
    return results(S_order().list_scoped(user, data))


@register_module("orders.set_loading_point", important=True)
@in_company_schema()
def set_loading_point(context, params, execution):
    """Hurgo elige el lugar de cargue del pedido (uno por viaje)."""
    user = context_user(context)
    data = validate_input(Sz_loading_point_in, context)
    S_order().set_loading_point(user, data["order_id"], data["address_id"])
    return _detail(user, data["order_id"])
