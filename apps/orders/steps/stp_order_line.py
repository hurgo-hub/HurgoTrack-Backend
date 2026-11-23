from enginedj.modules.registry import register_module

from apps.core.steps import context_user, results, validate_input
from apps.orders.serializers import Sz_pending_order_line
from apps.orders.services import S_order_line
from apps.orders.serializers import Sz_lookup_in


@register_module("orders.pending_lines", important=True)
def pending_lines(context, params, execution):
    """Líneas de pedidos confirmados con cantidad por despachar (para armar viajes)."""
    data = validate_input(Sz_lookup_in, context)
    lines = S_order_line().pending_for_trips(context_user(context), company_id=data.get("company_id"))
    return results(Sz_pending_order_line(lines, many=True).data)
