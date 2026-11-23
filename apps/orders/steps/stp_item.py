from enginedj.modules.registry import register_module

from enginedj.base.steps.helpers import context_user, results, validate_input
from apps.orders.serializers import Sz_item_lookup, Sz_lookup_in
from apps.orders.services import S_order


@register_module("orders.items", important=True)
def items_lookup(context, params, execution):
    """Productos que el usuario puede pedir. Filtros opcionales: company_id, q."""
    data = validate_input(Sz_lookup_in, context)
    items = S_order().items_lookup(context_user(context), company_id=data.get("company_id"), query=data.get("q", ""))
    return results(Sz_item_lookup(items, many=True).data)
