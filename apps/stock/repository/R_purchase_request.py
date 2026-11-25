from django.db.models import Prefetch

from enginedj.base.cache import InvalidateAppsMixin
from enginedj.base.repository import BaseRepositoryImpl

from apps.stock.entity import E_purchase_request
from apps.stock.models import M_purchase_request, M_purchase_request_line


class R_purchase_request(InvalidateAppsMixin, BaseRepositoryImpl[E_purchase_request]):
    invalidate_app_labels = ("stock",)

    def __init__(self):
        super().__init__(model=M_purchase_request, entity_class=E_purchase_request)
        self.model: M_purchase_request = self.model

    def create_request(self, **fields) -> M_purchase_request:
        request = self.model.objects.create(**fields)
        self._invalidate_list_cache()
        return request

    def add_lines(self, rows: list[M_purchase_request_line]):
        M_purchase_request_line.objects.bulk_create(rows)
        self._invalidate_list_cache()

    def get_for_update(self, request_id) -> M_purchase_request | None:
        return self.model.objects.select_for_update().filter(pk=request_id, is_active=True).first()

    def save_request(self, request: M_purchase_request, user, **fields):
        for name, value in fields.items():
            setattr(request, name, value)
        request.update_user = user
        request.save()
        self._invalidate_list_cache()
        return request

    def visible(self, company_ids=None):
        qs = self.model.objects.filter(is_active=True)
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        return qs

    def with_detail(self, qs):
        return qs.select_related("company_id", "create_user").prefetch_related(
            Prefetch(
                "purchase_request_line_purchase_request_id",
                queryset=M_purchase_request_line.objects.select_related("item_id", "order_line_id__order_id"),
            ),
            "odoo_purchases",
        )
