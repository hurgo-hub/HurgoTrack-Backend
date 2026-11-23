from datetime import timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from enginedj.base.repository import BaseRepositoryImpl

from apps.apiOdoo.entity import E_odoo_purchase
from apps.apiOdoo.models import M_odoo_purchase


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
            "update_user_id": user,
        }
        if values["date_order"] is not None and timezone.is_naive(values["date_order"]):
            values["date_order"] = timezone.make_aware(values["date_order"], dt_timezone.utc)
        purchase, _ = self.model.objects.update_or_create(odoo_id=data["id"], defaults=values)
        self._invalidate_list_cache()
        return purchase

    def get_by_name(self, name) -> M_odoo_purchase | None:
        return self.model.objects.filter(name=name, is_active=True).first()
