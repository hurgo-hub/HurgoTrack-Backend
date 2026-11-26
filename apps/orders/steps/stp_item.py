from enginedj.modules.registry import register_module

from enginedj.base.steps.helpers import context_user, results, validate_input
from apps.orders.serializers import Sz_company_items_in, Sz_item, Sz_item_in, Sz_item_lookup, Sz_lookup_in
from apps.orders.services import S_item, S_order


@register_module("orders.items", important=True)
def items_lookup(context, params, execution):
    """Productos que el usuario puede pedir. Filtros opcionales: company_id, q."""
    data = validate_input(Sz_lookup_in, context)
    items = S_order().items_lookup(context_user(context), company_id=data.get("company_id"), query=data.get("q", ""))
    return results(Sz_item_lookup(items, many=True).data)


@register_module("orders.company_items", important=True)
def company_items(context, params, execution):
    """Catálogo completo (activos e inactivos) de una empresa, para gestionarlo."""
    data = validate_input(Sz_company_items_in, context)
    return results(Sz_item(S_item().list(context_user(context), data["company_id"]), many=True).data)


@register_module("orders.item.save", important=True)
def save_item(context, params, execution):
    """Crea (sin item_id) o edita un producto de la empresa."""
    data = validate_input(Sz_item_in, context)
    return results(Sz_item(S_item().save(context_user(context), data)).data)
