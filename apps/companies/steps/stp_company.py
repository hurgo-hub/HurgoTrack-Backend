from enginedj.modules.registry import register_module

from apps.companies.serializers import Sz_recipient_lookup
from apps.companies.services import S_company
from apps.core.steps import context_user, results


@register_module("companies.recipients", important=True)
def recipients(context, params, execution):
    """Destinatarios con sus direcciones (para armar pedidos). Filtro opcional: q."""
    companies = S_company().recipients(context_user(context), context.get("q") or "")
    return results(Sz_recipient_lookup(companies, many=True).data)
