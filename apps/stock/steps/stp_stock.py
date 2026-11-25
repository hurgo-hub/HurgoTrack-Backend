"""Steps de stock. Cada uno es un workflow: POST /api/workflows/sync/<nombre>/."""

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

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
def requirements(context, params, execution):
    """Cuánto mandar a comprar por producto: pendiente por cargar − stock − ya solicitado."""
    data = validate_input(Sz_company_in, context)
    return results(Sz_requirement(S_stock().requirements(context_user(context), data["company_id"]), many=True).data)


@register_module("stock.list", important=True)
def list_stock(context, params, execution):
    data = validate_input(Sz_stock_list_in, context)
    rows = S_stock().list_stock(context_user(context), data.get("company_id"), data["only_available"])
    return results(Sz_stock(rows, many=True).data)


@register_module("stock.moves", important=True)
def list_moves(context, params, execution):
    """Kardex: entradas por compra, cargues a viajes y devoluciones."""
    data = validate_input(Sz_moves_in, context)
    rows = S_stock().list_moves(context_user(context), data.get("company_id"), data.get("item_id"))
    return results(Sz_stock_move(rows, many=True).data)


@register_module("stock.adjust", important=True)
def adjust(context, params, execution):
    data = validate_input(Sz_adjust_in, context)
    move = S_stock().adjust(context_user(context), company_id=data["company_id"], item_id=data["item_id"],
                            qty=data["qty"], reason=data["reason"])
    return results(Sz_stock_move(move).data if move else None)
