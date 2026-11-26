"""Steps de stock. Cada uno es un workflow: POST /api/workflows/sync/<nombre>/."""

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.companies.tenancy import for_each_company, in_company_schema

from apps.stock.serializers import (
    Sz_adjust_in,
    Sz_company_in,
    Sz_moves_in,
    Sz_requirement,
    Sz_stock,
    Sz_stock_list_in,
    Sz_stock_move,
)
from apps.stock.services import S_stock


@register_module("stock.requirements", important=True)
@in_company_schema()
def requirements(context, params, execution):
    """Cuánto mandar a comprar por producto: pendiente por cargar − stock − ya solicitado."""
    data = validate_input(Sz_company_in, context)
    return results(Sz_requirement(S_stock().requirements(context_user(context), data["company_id"]), many=True).data)


@register_module("stock.list", important=True)
@in_company_schema(optional=True)
def list_stock(context, params, execution):
    """Stock de una empresa o, para Hurgo sin company_id, el de todas (recorre sus esquemas)."""
    user = context_user(context)
    data = validate_input(Sz_stock_list_in, context)

    def rows(company_id):
        return Sz_stock(S_stock().list_stock(user, company_id, data["only_available"]), many=True).data

    return results(for_each_company(rows) if data.get("company_id") is None else rows(data["company_id"]))


@register_module("stock.moves", important=True)
@in_company_schema(optional=True)
def list_moves(context, params, execution):
    """Kardex: entradas por compra, cargues a viajes y devoluciones."""
    user = context_user(context)
    data = validate_input(Sz_moves_in, context)

    def rows(company_id):
        return Sz_stock_move(S_stock().list_moves(user, company_id, data.get("item_id")), many=True).data

    return results(for_each_company(rows) if data.get("company_id") is None else rows(data["company_id"]))


@register_module("stock.adjust", important=True)
@in_company_schema()
def adjust(context, params, execution):
    data = validate_input(Sz_adjust_in, context)
    move = S_stock().adjust(context_user(context), company_id=data["company_id"], item_id=data["item_id"],
                            qty=data["qty"], reason=data["reason"])
    return results(Sz_stock_move(move).data if move else None)
