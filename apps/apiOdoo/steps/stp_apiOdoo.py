"""Steps de la integración con Odoo (igual que stp_apiSintesis en arquitecturabase)."""

from enginedj.modules.registry import register_module

from apps.companies.tenancy import in_company_schema

from apps.apiOdoo.serializers import (
    Sz_odoo_purchase,
    Sz_order_id_in,
    Sz_purchase_in,
    Sz_sync_partners_in,
    Sz_sync_products_in,
)
from apps.apiOdoo.services import S_odoo_purchase, S_odoo_sync
from enginedj.base.services.permissions import has_perm
from enginedj.base.exceptions import BusinessPermissionError
from enginedj.base.steps.helpers import context_user, results, validate_input


@register_module("apiOdoo.get_purchase", important=True)
@in_company_schema()
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
@in_company_schema()
def get_create_products(context, params, execution):
    """Crea / actualiza productos de una empresa desde Odoo."""
    data = validate_input(Sz_sync_products_in, context)
    return results(S_odoo_sync().sync_products(context_user(context), data["company_id"], data["type_item_id"],
                                               data.get("domain"), data.get("limit")))


@register_module("apiOdoo.notify_delivery", important=True)
@in_company_schema()
def notify_delivery(context, params, execution):
    """Reenvía a Odoo la nota de entrega de un pedido (normalmente lo hace la tarea Celery)."""
    user = context_user(context)
    if not has_perm(user, "apiOdoo.sync_odoo"):
        raise BusinessPermissionError("No tienes permiso para sincronizar con Odoo.")
    data = validate_input(Sz_order_id_in, context)
    return results(S_odoo_sync().notify_delivery(data["order_id"], user))


# ----------------------------------------------------------------------
# Odoo simulado (ODOO_SIMULATED=True)
# ----------------------------------------------------------------------
from django.conf import settings  # noqa: E402
from rest_framework import serializers  # noqa: E402

from apps.apiOdoo.services import S_odoo_simulator  # noqa: E402


class Sz_simulate_in(serializers.Serializer):
    purchase_request_id = serializers.IntegerField(required=False, allow_null=True)
    order_id = serializers.IntegerField(required=False, allow_null=True)


@register_module("apiOdoo.mode", important=True)
def odoo_mode(context, params, execution):
    """Cómo está la integración: apagada, Odoo real o simulado (el frontend muestra el botón de simular)."""
    return results({"enabled": settings.ODOO_ENABLED, "simulated": settings.ODOO_SIMULATED})


@register_module("apiOdoo.simulate_purchase", important=True)
@in_company_schema()
def simulate_purchase(context, params, execution):
    """Crea en el Odoo simulado la compra de una solicitud de compra (o de un pedido); devuelve su referencia
    para registrarla después como una compra real."""
    data = validate_input(Sz_simulate_in, context)
    purchase = S_odoo_simulator().create_purchase(
        context_user(context), context["company_id"], purchase_request_id=data.get("purchase_request_id"),
        order_id=data.get("order_id"),
    )
    lines = purchase.odoo_purchase_line_purchase_id.order_by("odoo_line_id")
    return results({"name": purchase.name, "state": purchase.state,
                    "lines": [{"product": line.product_name, "qty": str(line.product_qty)} for line in lines]})

