from enginedj.modules.registry import register_module

from enginedj.base.steps.helpers import context_user, results, validate_input
from apps.companies.tenancy import for_each_company, in_company_schema
from apps.orders.serializers import Sz_lookup_in, Sz_pending_order_line
from apps.orders.services import S_order_line


@register_module("orders.pending_lines", important=True)
@in_company_schema(optional=True)
def pending_lines(context, params, execution):
    """Líneas de pedidos confirmados con cantidad por despachar (para armar viajes).
    Sin company_id (Hurgo): las de todas las empresas, recorriendo el esquema de cada una."""
    user = context_user(context)
    data = validate_input(Sz_lookup_in, context)

    def lines(company_id):
        return Sz_pending_order_line(S_order_line().pending_for_trips(user, company_id=company_id), many=True).data

    if data.get("company_id") is None:
        return results(for_each_company(lines))
    return results(lines(data["company_id"]))
