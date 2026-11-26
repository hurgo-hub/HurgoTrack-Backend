from enginedj.modules.registry import register_module

from apps.companies.tenancy import in_company_schema, trip_company

from enginedj.base.steps.helpers import context_user, validate_input
from apps.trips.serializers import Sz_series_in
from apps.trips.services import S_trip_line_serie
from apps.trips.steps.stp_trip import trip_detail


@register_module("trips.register_series", important=True)
@in_company_schema(company_from=trip_company)
def register_series(context, params, execution):
    """Registra las motos de una parada por VIN."""
    user = context_user(context)
    data = validate_input(Sz_series_in, context)
    S_trip_line_serie().register_series(user, data["trip_id"], data["trip_line_id"], data["series"])
    return trip_detail(user, data["trip_id"])
