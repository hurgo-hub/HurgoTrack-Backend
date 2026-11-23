from enginedj.modules.registry import register_module

from apps.core.steps import results
from apps.fleet.services import S_vehicle


@register_module("fleet.document_expirations", important=True)
def document_expirations(context, params, execution):
    """SOAT, revisión técnico-mecánica y licencias vencidas o por vencer."""
    days = context.get("days")
    return results(S_vehicle().document_expirations(int(days) if days not in (None, "") else None))
