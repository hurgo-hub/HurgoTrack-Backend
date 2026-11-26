"""Catálogo de productos de una empresa. Hurgo gestiona cualquier empresa; el admin de empresa, la suya."""

from decimal import Decimal

from django.db import IntegrityError, transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound
from enginedj.base.models import M_company
from enginedj.base.services.permissions import has_perm

from apps.orders.models import M_item, M_type_item


class S_item:

    @staticmethod
    def _require_company(user, company_id):
        if has_perm(user, "orders.create_any_company_order") or has_perm(user, "companies.create_company"):
            return
        from apps.companies.services import S_company

        S_company.require_manage(user, company_id)

    def list(self, user, company_id):
        self._require_company(user, company_id)
        return list(
            M_item.objects.filter(company_id=company_id).select_related("type_item_id", "brand_id")
            .prefetch_related("loading_tags").order_by("name")
        )

    @transaction.atomic
    def save(self, user, data: dict) -> M_item:
        """Crea (sin item_id) o edita un producto de la empresa."""
        self._require_company(user, data["company_id"])
        company = M_company.objects.filter(pk=data["company_id"], is_active=True).first()
        if company is None:
            raise BusinessNotFound("La empresa no existe.")
        type_item = M_type_item.objects.filter(pk=data["type_item_id"], is_active=True).first()
        if type_item is None:
            raise BusinessNotFound("El tipo de producto no existe.")
        if data.get("item_id"):
            item = M_item.objects.select_for_update().filter(pk=data["item_id"]).first()
            if item is None or item.company_id_id != company.pk:
                raise BusinessNotFound("El producto no es de esta empresa.")
            item.update_user = user
        else:
            item = M_item(company_id=company, create_user=user)
        item.type_item_id = type_item
        item.is_serialized = type_item.is_serialized
        for field in ("name", "description", "sku", "odoo_ref", "unit"):
            if field in data:
                setattr(item, field, (data[field] or "").strip() if field != "unit" else data[field])
        if "weight_kg" in data:
            item.weight_kg = data["weight_kg"] if data["weight_kg"] is None else Decimal(str(data["weight_kg"]))
        if "is_active" in data:
            item.is_active = data["is_active"]
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            raise BusinessError(f"Ya existe un producto con la referencia '{item.sku}' en esta empresa.",
                                code="duplicate_sku")
        if "loading_tag_ids" in data:
            from apps.locations.models import M_loading_tag

            item.loading_tags.set(M_loading_tag.objects.filter(pk__in=data["loading_tag_ids"], is_active=True))
        return item
