"""Tareas Celery de flota."""

import logging

from celery import shared_task

from apps.fleet.services import S_vehicle

logger = logging.getLogger(__name__)


@shared_task(name="fleet.tasks.check_document_expirations")
def check_document_expirations(days: int | None = None) -> dict:
    """Programada a diario en CELERY_BEAT_SCHEDULE. Por ahora reporta; las alertas (fase 2) se conectan aquí."""
    result = S_vehicle().document_expirations(days)
    logger.info(
        "Documentos por vencer hasta %s: %s SOAT, %s RTM, %s licencias",
        result["until"], len(result["soat"]), len(result["mechanical_inspection"]), len(result["driver_license"]),
    )
    return result
