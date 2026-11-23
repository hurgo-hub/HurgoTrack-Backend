"""Steps de la integración con Odoo (igual que stp_apiSintesis en arquitecturabase)."""

from enginedj.modules.registry import register_module

from apps.apiOdoo.serializers import (
    Sz_odoo_purchase,
    Sz_order_id_in,
    Sz_purchase_in,
    Sz_sync_partners_in,
    Sz_sync_products_in,
)
from apps.apiOdoo.services import S_odoo_purchase, S_odoo_sync
from apps.core.permissions import has_perm
from apps.core.exceptions import BusinessPermissionError
from apps.core.steps import context_user, results, validate_input


@register_module("apiOdoo.get_purchase", important=True)
def get_purchase(context, params, execution):
    """Consulta una compra en Odoo (por referencia) y actualiza la copia local."""
    user = context_user(context)
    if not (has_perm(user, "apiOdoo.sync_odoo") or has_perm(user, "orders.confirm_order")):
        raise BusinessPermissionError("No tienes permiso para consultar compras de Odoo.")
    data = validate_input(Sz_purchase_in, context)
    return results(Sz_odoo_purchase(S_odoo_purchase().sync_by_name(data["name"], user)).data)


@register_module("apiOdoo.get_create_partners", important=True)
def get_create_partners(context, params, execution):
    """Crea / actualiza empresas desde los contactos de Odoo."""
    data = validate_input(Sz_sync_partners_in, context)
    return results(S_odoo_sync().sync_partners(context_user(context), data.get("domain"), data.get("limit")))


@register_module("apiOdoo.get_create_products", important=True)
def get_create_products(context, params, execution):
    """Crea / actualiza productos de una empresa desde Odoo."""
    data = validate_input(Sz_sync_products_in, context)
    return results(S_odoo_sync().sync_products(context_user(context), data["company_id"], data["type_item_id"],
                                               data.get("domain"), data.get("limit")))


@register_module("apiOdoo.notify_delivery", important=True)
def notify_delivery(context, params, execution):
    """Reenvía a Odoo la nota de entrega de un pedido (normalmente lo hace la tarea Celery)."""
    user = context_user(context)
    if not has_perm(user, "apiOdoo.sync_odoo"):
        raise BusinessPermissionError("No tienes permiso para sincronizar con Odoo.")
    data = validate_input(Sz_order_id_in, context)
    return results(S_odoo_sync().notify_delivery(data["order_id"], user))
