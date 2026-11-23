"""Tareas Celery de la integración con Odoo."""

import logging

import requests
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="apiOdoo.tasks.notify_order_delivered",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    max_retries=5,
)
def notify_order_delivered(order_id: int) -> dict:
    """Al quedar entregado un pedido, deja la nota de entrega en la compra de Odoo (reintenta si Odoo no responde)."""
    from apps.apiOdoo.services import S_odoo_sync

    result = S_odoo_sync().notify_delivery(order_id)
    logger.info("Entrega del pedido %s notificada a Odoo (%s)", result["order"], result["purchase"])
    return result
