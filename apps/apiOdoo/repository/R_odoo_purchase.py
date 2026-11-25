from datetime import timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from enginedj.base.repository import BaseRepositoryImpl

from apps.apiOdoo.entity import E_odoo_purchase
from decimal import Decimal

from apps.apiOdoo.models import M_odoo_purchase, M_odoo_purchase_line


def _m2o(value):
    """Many2one de Odoo: [id, "nombre"] -> (id, nombre)."""
    if isinstance(value, (list, tuple)) and value:
        return value[0], (value[1] if len(value) > 1 else "")
    return None, ""


class R_odoo_purchase(BaseRepositoryImpl[E_odoo_purchase]):

    def __init__(self):
        super().__init__(model=M_odoo_purchase, entity_class=E_odoo_purchase)
        self.model: M_odoo_purchase = self.model

    def upsert_from_odoo(self, data: dict, user=None) -> M_odoo_purchase:
        partner = data.get("partner_id") or [None, ""]
        date_order = data.get("date_order")
        values = {
            "name": data.get("name") or "",
            "partner_odoo_id": partner[0] if isinstance(partner, (list, tuple)) else None,
            "partner_name": partner[1] if isinstance(partner, (list, tuple)) else "",
            "state": data.get("state") or "",
            "date_order": parse_datetime(date_order.replace(" ", "T")) if isinstance(date_order, str) else None,
            "amount_total": data.get("amount_total"),
            "raw": data,
            "synced_date": timezone.now(),
            "update_user": user,
        }
        if values["date_order"] is not None and timezone.is_naive(values["date_order"]):
            values["date_order"] = timezone.make_aware(values["date_order"], dt_timezone.utc)
        purchase, _ = self.model.objects.update_or_create(odoo_id=data["id"], defaults=values)
        self._invalidate_list_cache()
        return purchase

    def upsert_lines_from_odoo(self, purchase: M_odoo_purchase, lines: list[dict], user=None) -> list[M_odoo_purchase_line]:
        """Guarda las líneas de la compra. No toca ``qty_stocked`` (lo maneja la app stock)."""
        rows = []
        for data in lines:
            product_id, product_name = _m2o(data.get("product_id"))
            _, uom_name = _m2o(data.get("product_uom"))
            row, _ = M_odoo_purchase_line.objects.update_or_create(
                odoo_line_id=data["id"],
                defaults={
                    "purchase_id": purchase,
                    "product_odoo_id": product_id,
                    "product_name": product_name or data.get("name") or "",
                    "product_qty": Decimal(str(data.get("product_qty") or 0)),
                    "qty_received": Decimal(str(data.get("qty_received") or 0)),
                    "uom_name": uom_name,
                    "raw": data,
                    "update_user": user,
                },
            )
            rows.append(row)
        self._invalidate_list_cache()
        return rows

    def lines_for_update(self, purchase: M_odoo_purchase) -> list[M_odoo_purchase_line]:
        return list(M_odoo_purchase_line.objects.select_for_update().filter(purchase_id=purchase).order_by("odoo_line_id"))

    def get_by_name(self, name) -> M_odoo_purchase | None:
        return self.model.objects.filter(name=name, is_active=True).first()
