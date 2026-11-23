from django.db.models import Q

from enginedj.base.repository import BaseRepositoryImpl

from enginedj.base.cache import InvalidateAppsMixin
from apps.orders.entity import E_item
from apps.orders.models import M_item


class R_item(InvalidateAppsMixin, BaseRepositoryImpl[E_item]):
    invalidate_app_labels = ("orders", "trips")  # los listados de viajes y pedidos se cruzan

    def __init__(self):
        super().__init__(model=M_item, entity_class=E_item)
        self.model: M_item = self.model

    def active_by_ids(self, item_ids, company_id) -> dict[int, M_item]:
        return {
            item.pk: item
            for item in self.model.objects.filter(pk__in=item_ids, company_id=company_id, is_active=True)
        }

    def lookup(self, company_ids=None, company_id=None, query: str = "", limit: int = 50) -> list[M_item]:
        qs = self.model.objects.filter(is_active=True).select_related("type_item_id", "brand_id")
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        if company_id:
            qs = qs.filter(company_id=company_id)
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query))
        return list(qs.order_by("name")[:limit])
