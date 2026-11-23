"""Steps de la integración con Satrack: datos listos para los componentes de mapcn."""

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.apiSatrack.serializers import Sz_history_in, Sz_map_overview_in, Sz_positions_in, Sz_trip_map_in
from apps.apiSatrack.services import S_satrack, S_satrack_map


@register_module("apiSatrack.positions")
def positions(context, params, execution):
    """Última posición de los vehículos de la flota (todos, o ``vehicle_ids`` / ``plates``)."""
    data = validate_input(Sz_positions_in, context)
    return results(S_satrack().fleet_positions(data.get("vehicle_ids"), data.get("plates")))


@register_module("apiSatrack.history")
def history(context, params, execution):
    """Recorrido de un vehículo entre ``start`` y ``end`` (máximo 5 días atrás) para ``MapRoute``."""
    data = validate_input(Sz_history_in, context)
    service = S_satrack()
    vehicle = service.vehicle(data.get("vehicle_id"), data.get("plate"))
    return results(service.history(vehicle, data.get("start"), data.get("end"), data.get("event_codes")))


@register_module("apiSatrack.map_overview")
def map_overview(context, params, execution):
    """Viajes activos que el usuario puede ver: arcos, paradas y vehículos."""
    data = validate_input(Sz_map_overview_in, context)
    return results(S_satrack_map().overview(context_user(context), data["arc_mode"], data.get("trip_ids")))


@register_module("apiSatrack.trip_map")
def trip_map(context, params, execution):
    """Un viaje: arcos, paradas, vehículo y recorrido desde la salida."""
    data = validate_input(Sz_trip_map_in, context)
    return results(S_satrack_map().trip_map(context_user(context), data["trip_id"], data["arc_mode"],
                                            data["with_route"]))
