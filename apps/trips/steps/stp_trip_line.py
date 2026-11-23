from enginedj.modules.registry import register_module

from apps.core.exceptions import BusinessError
from apps.core.steps import context_files, context_user, validate_files, validate_input
from apps.trips.serializers import Sz_deliver_in, Sz_return_in, Sz_stop_position_in, validate_attach
from apps.trips.services import S_trip_line
from apps.trips.steps.stp_trip import trip_detail


@register_module("trips.start_delivery", important=True)
def start_delivery(context, params, execution):
    """Paso 5: el conductor llega a la parada (en reparto)."""
    user = context_user(context)
    data = validate_input(Sz_stop_position_in, context)
    S_trip_line().start_delivery(user, data["trip_id"], data["trip_line_id"], latitude=data.get("latitude"),
                                 longitude=data.get("longitude"))
    return trip_detail(user, data["trip_id"])


@register_module("trips.deliver", important=True)
def deliver(context, params, execution):
    """Paso 7: entrega con la foto de la remisión firmada (multipart, primer archivo de "files")."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_deliver_in, context)
    if not files:
        raise BusinessError("La entrega se confirma con la foto de la remisión firmada.", code="missing_proof")
    S_trip_line().deliver(user, data["trip_id"], data["trip_line_id"], proof=files[0], rating=data.get("rating"),
                          comment=data.get("comment", ""), latitude=data.get("latitude"),
                          longitude=data.get("longitude"))
    return trip_detail(user, data["trip_id"])


@register_module("trips.register_return", important=True)
def register_return(context, params, execution):
    """Devolución de la parada completa (fotos opcionales en "files")."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_return_in, context)
    S_trip_line().register_return(user, data["trip_id"], data["trip_line_id"], reason=data["reason"], files=files,
                                  latitude=data.get("latitude"), longitude=data.get("longitude"))
    return trip_detail(user, data["trip_id"])
