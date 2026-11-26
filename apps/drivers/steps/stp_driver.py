"""Gestión de conductores (administración de Hurgo)."""

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.drivers.serializers import Sz_driver, Sz_driver_in
from apps.drivers.services import S_driver_admin


@register_module("drivers.list", important=True)
def list_drivers(context, params, execution):
    """Conductores (activos e inactivos) con su usuario, documento y licencia."""
    return results(Sz_driver(S_driver_admin().list(context_user(context)), many=True).data)


@register_module("drivers.save", important=True)
def save_driver(context, params, execution):
    """Crea (sin driver_id: usuario nuevo o user_id) o edita un conductor."""
    service = S_driver_admin()
    driver = service.save(context_user(context), validate_input(Sz_driver_in, context))
    return results(Sz_driver(service.detail(driver.pk)).data)
