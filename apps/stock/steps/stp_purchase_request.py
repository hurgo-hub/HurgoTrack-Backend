"""Steps de solicitudes de compra (Hurgo -> facturador -> compra en Odoo -> stock)."""

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.stock.serializers import (
    Sz_link_purchase_in,
    Sz_purchase_request,
    Sz_request_cancel_in,
    Sz_request_id_in,
    Sz_request_in,
    Sz_request_list_in,
)
from apps.stock.services import S_purchase_request


def _detail(user, request_id, **extra):
    data = Sz_purchase_request(S_purchase_request().detail(user, request_id)).data
    return results({**data, **extra})


@register_module("stock.purchase_request.create", important=True)
def create_request(context, params, execution):
    """Hurgo pide la compra al facturador. lines: [{item_id, qty, order_line_id?}]."""
    user = context_user(context)
    data = validate_input(Sz_request_in, context)
    request = S_purchase_request().create(user, company_id=data["company_id"], lines=data["lines"],
                                          notes=data["notes"], send=data["send"])
    return _detail(user, request.pk)


@register_module("stock.purchase_request.send", important=True)
def send_request(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_request_id_in, context)
    S_purchase_request().send(user, data["purchase_request_id"])
    return _detail(user, data["purchase_request_id"])


@register_module("stock.purchase_request.link_purchase", important=True)
def link_purchase(context, params, execution):
    """El facturador registra la compra de Odoo (P000XX): sus líneas entran al stock de la empresa."""
    user = context_user(context)
    data = validate_input(Sz_link_purchase_in, context)
    request, summary = S_purchase_request().link_purchase(user, data["purchase_request_id"], data["odoo_purchase"])
    return _detail(user, request.pk, stock_summary=summary)


@register_module("stock.purchase_request.cancel", important=True)
def cancel_request(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_request_cancel_in, context)
    S_purchase_request().cancel(user, data["purchase_request_id"], data["reason"])
    return _detail(user, data["purchase_request_id"])


@register_module("stock.purchase_request.retrieve", important=True)
def retrieve_request(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_request_id_in, context)
    return _detail(user, data["purchase_request_id"])


@register_module("stock.purchase_request.list", important=True)
def list_requests(context, params, execution):
    data = validate_input(Sz_request_list_in, context)
    rows = S_purchase_request().list_scoped(context_user(context), company_id=data.get("company_id"),
                                            state=data.get("state"))
    return results(Sz_purchase_request(rows, many=True).data)
