"""Gestión de la flota de Hurgo: vehículos, propietarios, SOAT y revisión técnico-mecánica."""

from enginedj.base.steps.helpers import context_files, context_user, results, validate_files, validate_input
from enginedj.modules.registry import register_module

from apps.fleet.serializers import (
    Sz_partner, Sz_partner_in, Sz_rtm, Sz_rtm_in, Sz_soat, Sz_soat_in, Sz_vehicle, Sz_vehicle_in,
)
from apps.fleet.services import S_fleet
from apps.trips.serializers import validate_attach


def _one_file(context):
    files = validate_files(context_files(context), validate_attach)
    return files[0] if files else None


@register_module("fleet.lookups", important=True)
def fleet_lookups(context, params, execution):
    """Tipos, marcas, carrocerías, organismos de tránsito y propietarios activos (para los formularios)."""
    return results(S_fleet().lookups(context_user(context)))


@register_module("fleet.vehicles", important=True)
def fleet_vehicles(context, params, execution):
    """Vehículos (activos e inactivos) con su último SOAT y revisión técnico-mecánica."""
    return results(Sz_vehicle(S_fleet().vehicles(context_user(context)), many=True).data)


@register_module("fleet.vehicle.save", important=True)
def save_vehicle(context, params, execution):
    """Crea (sin vehicle_id) o edita un vehículo. Queda a nombre de la empresa Hurgo."""
    data = validate_input(Sz_vehicle_in, context)
    service = S_fleet()
    vehicle = service.save_vehicle(context_user(context), data)
    return results(Sz_vehicle(service.vehicle_detail(vehicle.pk)).data)


@register_module("fleet.partners", important=True)
def fleet_partners(context, params, execution):
    """Propietarios y tenedores de vehículos (terceros)."""
    return results(Sz_partner(S_fleet().partners(context_user(context)), many=True).data)


@register_module("fleet.partner.save", important=True)
def save_partner(context, params, execution):
    data = validate_input(Sz_partner_in, context)
    return results(Sz_partner(S_fleet().save_partner(context_user(context), data)).data)


@register_module("fleet.soat.save", important=True)
def save_soat(context, params, execution):
    """Registra el SOAT (o su renovación). Multipart: vehicle_id, insurer_name, policy_number, date_start,
    date_expire y, opcional, ``files`` con la póliza."""
    user = context_user(context)
    file = _one_file(context)
    data = validate_input(Sz_soat_in, context)
    return results(Sz_soat(S_fleet().add_soat(user, data, file)).data)


@register_module("fleet.rtm.save", important=True)
def save_rtm(context, params, execution):
    """Registra la revisión técnico-mecánica (o su renovación). Multipart: vehicle_id, certificate_number,
    cda_name, date_expedition, date_expire y, opcional, ``files`` con el certificado."""
    user = context_user(context)
    file = _one_file(context)
    data = validate_input(Sz_rtm_in, context)
    return results(Sz_rtm(S_fleet().add_rtm(user, data, file)).data)
