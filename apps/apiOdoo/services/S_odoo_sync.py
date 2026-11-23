"""Sincronización Hurgo Track <-> Odoo.

- Contactos (res.partner) -> M_company (por odoo_ref).
- Productos (product.product) -> M_item de una empresa (por odoo_ref).
- Pedido entregado -> nota en el chatter de la compra (purchase.order).

Odoo sigue llevando la compra, el recibo y la factura; Hurgo Track lleva la logística.
"""

from django.db import transaction
from django.utils.html import escape

from apps.apiOdoo.services.apiService import ApiOdooService
from apps.apiOdoo.services.S_odoo_purchase import S_odoo_purchase
from apps.apiOdoo.services.S_odoo_sync_log import S_odoo_sync_log
from enginedj.base.exceptions import BusinessError, BusinessNotFound
from enginedj.base.services.permissions import require_perm


def split_vat(vat: str) -> tuple[str, str]:
    """'900.123.456-7' -> ('900123456', '7')."""
    vat = (vat or "").upper().replace("CO", "").replace(".", "").replace(" ", "").strip()
    number, _, digit = vat.partition("-")
    return number, digit[:1]


class S_odoo_sync:

    def __init__(self):
        self.api = ApiOdooService()
        self.log = S_odoo_sync_log()

    @transaction.atomic
    def sync_partners(self, user, domain=None, limit=None) -> dict:
        """Crea / actualiza empresas desde Odoo. Las que no tienen NIT (vat) se omiten."""
        from enginedj.base.models import M_company

        require_perm(user, "apiOdoo.sync_odoo", "No tienes permiso para sincronizar con Odoo.")
        partners = self.api.get_partners(domain, limit)
        summary = {"created": 0, "updated": 0, "skipped": []}
        for partner in partners:
            number, digit = split_vat(partner.get("vat") or "")
            if not number:
                summary["skipped"].append({"odoo_id": partner["id"], "name": partner.get("name"), "reason": "sin NIT"})
                continue
            company = (M_company.objects.filter(odoo_ref=str(partner["id"])).first()
                       or M_company.objects.filter(document_number=number).first())
            values = {"name": partner.get("name") or number, "document_number": number, "verification_digit": digit,
                      "email": partner.get("email") or "", "phone": partner.get("phone") or "",
                      "odoo_ref": str(partner["id"])}
            if company is None:
                M_company.objects.create(create_user=user, **values)
                summary["created"] += 1
            else:
                for key, value in values.items():
                    setattr(company, key, value)
                company.update_user = user
                company.save()
                summary["updated"] += 1
        self.log.success("sync_partners", summary, odoo_model="res.partner", user=user)
        return summary

    @transaction.atomic
    def sync_products(self, user, company_id, type_item_id, domain=None, limit=None) -> dict:
        """Crea / actualiza productos de una empresa cliente desde Odoo."""
        from enginedj.base.models import M_company
        from apps.orders.models import M_item, M_type_item

        require_perm(user, "apiOdoo.sync_odoo", "No tienes permiso para sincronizar con Odoo.")
        company = M_company.objects.filter(pk=company_id, is_active=True).first()
        type_item = M_type_item.objects.filter(pk=type_item_id, is_active=True).first()
        if company is None or type_item is None:
            raise BusinessNotFound("Indica una empresa y un tipo de producto existentes.")
        summary = {"created": 0, "updated": 0}
        for product in self.api.get_products(domain, limit):
            values = {"name": product.get("name") or "", "sku": product.get("default_code") or "",
                      "weight_kg": product.get("weight") or None}
            item = M_item.objects.filter(company_id=company, odoo_ref=str(product["id"])).first()
            if item is None:
                M_item.objects.create(company_id=company, type_item_id=type_item, odoo_ref=str(product["id"]),
                                      is_serialized=type_item.is_serialized, create_user=user, **values)
                summary["created"] += 1
            else:
                for key, value in values.items():
                    setattr(item, key, value)
                item.update_user = user
                item.save()
                summary["updated"] += 1
        self.log.success("sync_products", summary, odoo_model="product.product", reference=company.name, user=user)
        return summary

    def notify_delivery(self, order_id, user=None) -> dict:
        """Deja en la compra de Odoo la nota de entrega del pedido (lo llama la tarea Celery al entregar)."""
        from apps.orders.models import M_order

        order = M_order.objects.filter(pk=order_id).first()
        if order is None:
            raise BusinessNotFound("El pedido no existe.")
        if not order.odoo_purchase:
            raise BusinessError(f"El pedido {order.code} no tiene compra de Odoo.", code="odoo_required")
        purchase = S_odoo_purchase().get_or_sync(order.odoo_purchase, user)
        rows = "".join(
            f"<li>{escape(line.item_id.name)}: {line.qty_delivered} → {escape(line.recipient_id.name)}</li>"
            for line in order.order_line_order_id.select_related("item_id", "recipient_id")
        )
        body = f"<p>Pedido <b>{escape(order.code)}</b> entregado por Hurgo Track.</p><ul>{rows}</ul>"
        try:
            result = self.api.post_message("purchase.order", purchase.odoo_id, body)
        except Exception as exc:
            self.log.error("notify_delivery", exc, odoo_model="purchase.order", reference=order.code, user=user)
            raise
        self.log.success("notify_delivery", result, odoo_model="purchase.order", reference=order.code,
                         request={"body": body}, user=user)
        return {"order": order.code, "purchase": purchase.name, "message_id": result}
