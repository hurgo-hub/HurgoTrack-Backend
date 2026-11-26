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
def notify_order_delivered(order_id: int, company_id: int) -> dict:
    """Al quedar entregado un pedido, deja la nota de entrega en la compra de Odoo (reintenta si Odoo no responde).
    El pedido vive en el esquema de su empresa."""
    from apps.apiOdoo.services import S_odoo_sync
    from apps.companies.tenancy import company_schema

    with company_schema(company_id):
        result = S_odoo_sync().notify_delivery(order_id)
    logger.info("Entrega del pedido %s notificada a Odoo (%s)", result["order"], result["purchase"])
    return result
