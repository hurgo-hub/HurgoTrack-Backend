"""Tareas Celery de conductores."""

import requests
from celery import shared_task


@shared_task(name="drivers.tasks.send_push", autoretry_for=(requests.RequestException,), retry_backoff=True,
             max_retries=5)
def send_push(user_ids, title, body, data=None):
    """Notificación push a la app del conductor (reintenta si Expo no responde)."""
    from apps.drivers.services.S_push import send_now

    return send_now(user_ids, title, body, data)
