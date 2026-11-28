"""Celular del conductor: registrar / quitar el token de notificaciones (app móvil)."""

from rest_framework import serializers

from enginedj.base.steps.helpers import context_user, results, validate_input
from enginedj.modules.registry import register_module

from apps.drivers.services.S_push import register_device, unregister_device


class Sz_device_in(serializers.Serializer):
    push_token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=["android", "ios"], required=False, default="android")
    app_version = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")


@register_module("mobile.device.register", important=True)
def register(context, params, execution):
    """Al iniciar sesión en la app: aquí llegan las notificaciones de sus viajes."""
    data = validate_input(Sz_device_in, context)
    device = register_device(context_user(context), data["push_token"], data["platform"], data["app_version"])
    return results({"id": device.pk, "platform": device.platform})


@register_module("mobile.device.unregister", important=True)
def unregister(context, params, execution):
    """Al cerrar sesión en la app: ese celular deja de recibir notificaciones."""
    data = validate_input(Sz_device_in, context)
    unregister_device(context_user(context), data["push_token"])
    return results({"ok": True})
