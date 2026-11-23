from enginedj.modules.registry import register_module

from enginedj.base.steps.helpers import context_files, context_user, validate_files, validate_input
from apps.trips.serializers import Sz_novelty_in, validate_attach
from apps.trips.services import S_trip_event
from apps.trips.steps.stp_trip import trip_detail


@register_module("trips.report_novelty", important=True)
def report_novelty(context, params, execution):
    """Paso 6: novedad del recorrido (fotos opcionales en "files")."""
    user = context_user(context)
    files = validate_files(context_files(context), validate_attach)
    data = validate_input(Sz_novelty_in, context)
    S_trip_event().report_novelty(user, data["trip_id"], name=data["name"], description=data.get("description", ""),
                                  trip_line_id=data.get("trip_line_id"), files=files,
                                  latitude=data.get("latitude"), longitude=data.get("longitude"))
    return trip_detail(user, data["trip_id"])
