"""Notificaciones push a la app del conductor (Expo Push -> Firebase).

El servidor no guarda credenciales de Firebase: Expo entrega con las que se subieron a EAS.
Se envía después de guardar (``transaction.on_commit``) y en Celery, para no frenar la petición.
``PUSH_ENABLED=False`` (por defecto) no envía nada.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from enginedj.base.exceptions import BusinessError

logger = logging.getLogger(__name__)


def register_device(user, push_token, platform="android", app_version=""):
    from apps.drivers.models import M_device

    push_token = (push_token or "").strip()
    if not push_token.startswith(("ExponentPushToken[", "ExpoPushToken[")):
        raise BusinessError("Token de notificaciones inválido.", code="invalid_push_token")
    device, _ = M_device.objects.update_or_create(push_token=push_token, defaults={
        "user_id": user, "platform": platform or "android", "app_version": app_version or "",
        "last_seen": timezone.now(), "is_active": True, "update_user": user,
    })
    return device


def unregister_device(user, push_token):
    from apps.drivers.models import M_device

    M_device.objects.filter(user_id=user, push_token=(push_token or "").strip()).update(is_active=False)


def notify_driver(driver, title, body, trip=None, kind="info"):
    """Avisa al conductor en todos sus celulares activos, después de que se guarde la transacción."""
    if not settings.PUSH_ENABLED or driver is None:
        return
    user_id = driver.user_id_id
    data = {"kind": kind, **({"trip_id": trip.pk, "trip_code": trip.code} if trip is not None else {})}

    def enqueue():
        # Si la cola (Redis) o Expo fallan, el viaje igual queda asignado: solo se registra el error
        try:
            from apps.drivers.tasks import send_push

            send_push.delay([user_id], title, body, data)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo enviar la notificación al conductor %s", user_id)

    transaction.on_commit(enqueue)


def send_now(user_ids, title, body, data=None) -> dict:
    """Envía ya a la API de Expo (lo llama la tarea). Desactiva los tokens que Expo dice que ya no sirven."""
    import requests

    from apps.drivers.models import M_device

    tokens = list(M_device.objects.filter(user_id__in=user_ids, is_active=True).values_list("push_token", flat=True))
    if not tokens:
        return {"sent": 0}
    messages = [{"to": t, "title": title, "body": body, "data": data or {}, "sound": "default",
                 "priority": "high", "channelId": "viajes"} for t in tokens]
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if settings.EXPO_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"
    response = requests.post(settings.EXPO_PUSH_URL, json=messages, headers=headers, timeout=15)
    response.raise_for_status()
    tickets = response.json().get("data") or []
    dead = [tokens[i] for i, t in enumerate(tickets)
            if t.get("status") == "error" and (t.get("details") or {}).get("error") == "DeviceNotRegistered"]
    if dead:
        M_device.objects.filter(push_token__in=dead).update(is_active=False)
    errors = [t for t in tickets if t.get("status") == "error"]
    if errors:
        logger.warning("Expo rechazó %s notificaciones: %s", len(errors), errors)
    return {"sent": len(tokens) - len(errors), "errors": len(errors), "disabled": len(dead)}
