"""Steps del viaje. Cada uno se expone como workflow: POST /api/workflows/sync/<nombre>/."""

from enginedj.modules.registry import register_module

from apps.companies.tenancy import in_company_schema, trip_company

from enginedj.base.steps.helpers import context_user, results, validate_input
from apps.trips.serializers import (
    Sz_allocations_in,
    Sz_assign_in,
    Sz_cancel_in,
    Sz_depart_in,
    Sz_reject_in,
    Sz_return_trip_in,
    Sz_trip_build_in,
    Sz_trip_detail,
    Sz_trip_driver,
    Sz_trip_id_in,
)
from apps.trips.services import S_trip


def trip_detail(user, trip_id):
    return results(Sz_trip_detail(S_trip().detail(user, trip_id)).data)


@register_module("trips.build", important=True)
@in_company_schema()
def build_trip(context, params, execution):
    """Paso 3: despacho arma el viaje con líneas de pedido confirmadas."""
    user = context_user(context)
    data = validate_input(Sz_trip_build_in, context)
    trip = S_trip().build(user, company_id=data["company_id"], origin_address_id=data.get("origin_address_id"),
                          allocations=data["allocations"], planned_departure=data.get("planned_departure"),
                          notes=data.get("notes", ""))
    return trip_detail(user, trip.pk)


@register_module("trips.add_allocations", important=True)
@in_company_schema(company_from=trip_company)
def add_allocations(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_allocations_in, context)
    S_trip().add_allocations(user, data["trip_id"], data["allocations"])
    return trip_detail(user, data["trip_id"])


@register_module("trips.assign", important=True)
@in_company_schema(company_from=trip_company)
def assign_trip(context, params, execution):
    """Paso 3: asigna vehículo y conductor."""
    user = context_user(context)
    data = validate_input(Sz_assign_in, context)
    S_trip().assign(user, data["trip_id"], vehicle_id=data["vehicle_id"], driver_id=data["driver_id"],
                    carrier_id=data.get("carrier_id"))
    return trip_detail(user, data["trip_id"])


@register_module("trips.cancel", important=True)
@in_company_schema(company_from=trip_company)
def cancel_trip(context, params, execution):
    user = context_user(context)
    data = validate_input(Sz_cancel_in, context)
    S_trip().cancel(user, data["trip_id"], data["reason"])
    return trip_detail(user, data["trip_id"])


@register_module("trips.accept", important=True)
@in_company_schema(company_from=trip_company)
def accept_trip(context, params, execution):
    """El conductor acepta el viaje que le asignaron (app)."""
    user = context_user(context)
    data = validate_input(Sz_trip_id_in, context)
    S_trip().accept(user, data["trip_id"])
    return trip_detail(user, data["trip_id"])


@register_module("trips.reject", important=True)
@in_company_schema(company_from=trip_company)
def reject_trip(context, params, execution):
    """El conductor rechaza el viaje con el motivo; vuelve a despacho para asignar otro conductor."""
    user = context_user(context)
    data = validate_input(Sz_reject_in, context)
    trip = S_trip().reject(user, data["trip_id"], data["reason"])
    return results({"id": trip.pk, "code": trip.code, "state": trip.state})  # ya no es su viaje


@register_module("trips.depart", important=True)
@in_company_schema(company_from=trip_company)
def depart_trip(context, params, execution):
    """Paso 4: el conductor sale a ruta."""
    user = context_user(context)
    data = validate_input(Sz_depart_in, context)
    S_trip().depart(user, data["trip_id"], latitude=data.get("latitude"), longitude=data.get("longitude"))
    return trip_detail(user, data["trip_id"])


@register_module("trips.create_return_trip", important=True)
@in_company_schema(company_from=trip_company)
def create_return_trip(context, params, execution):
    """Despacho genera el viaje de regreso de una parada devuelta."""
    user = context_user(context)
    data = validate_input(Sz_return_trip_in, context)
    new_trip = S_trip().create_return_trip(user, data["trip_id"], data["trip_line_id"],
                                           origin_address_id=data.get("origin_address_id"))
    return trip_detail(user, new_trip.pk)


@register_module("trips.retrieve", important=True)
@in_company_schema(company_from=trip_company)
def retrieve_trip(context, params, execution):
    """Detalle con paradas, productos, VIN, eventos y fotos."""
    user = context_user(context)
    data = validate_input(Sz_trip_id_in, context)
    return trip_detail(user, data["trip_id"])


@register_module("trips.list", important=True)
def list_trips(context, params, execution):
    """Igual que list.relations (data: fields, relations, filters...), limitado a lo que el usuario ve."""
    return results(S_trip().list_scoped(context_user(context), context.get("data") or {}))


@register_module("trips.mine", important=True)
def my_trips(context, params, execution):
    """Paso 4: viajes activos del conductor (app móvil)."""
    return results(Sz_trip_driver(S_trip().mine(context_user(context)), many=True).data)


@register_module("trips.resources", important=True)
def resources(context, params, execution):
    """Vehículos y conductores activos para asignar a un viaje."""
    return results(S_trip().resources(context_user(context)))
