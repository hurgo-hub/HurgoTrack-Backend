from enginedj.base.steps.helpers import context_user, results
from enginedj.modules.registry import register_module

from apps.locations.serializers import Sz_recipient_lookup
from apps.locations.services import S_address


@register_module("locations.recipients", important=True)
def recipients(context, params, execution):
    """Destinatarios con sus direcciones (para armar pedidos). Filtro opcional: q."""
    addresses = S_address().recipients(context_user(context), context.get("q") or "")
    return results(Sz_recipient_lookup(addresses, many=True).data)
