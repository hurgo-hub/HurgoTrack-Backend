from django.db.models import Q

from enginedj.base.repository import BaseRepositoryImpl

from apps.locations.entity import E_address
from apps.locations.models import M_address


class R_address(BaseRepositoryImpl[E_address]):

    def __init__(self):
        super().__init__(model=M_address, entity_class=E_address)
        self.model: M_address = self.model

    def get_active(self, address_id) -> M_address | None:
        return self.model.objects.filter(pk=address_id, is_active=True).first()

    def loading_points(self, company_id=None, tag_ids=None, query: str = "", limit: int = 200) -> list[M_address]:
        """Lugares de cargue activos, con sus etiquetas precargadas."""
        qs = (
            self.model.objects.filter(is_active=True)
            .select_related("company_id", "location_id")
            .prefetch_related("tags")
        )
        if company_id:
            qs = qs.filter(company_id=company_id)
        if tag_ids:
            qs = qs.filter(tags__in=tag_ids).distinct()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(address__icontains=query) | Q(company_id__name__icontains=query))
        return list(qs.order_by("name")[:limit])

    def get_for_update(self, address_id) -> M_address | None:
        return self.model.objects.select_for_update().filter(pk=address_id).first()

    def save_address(self, address: M_address, user, tags=None) -> M_address:
        if address.pk is None:
            address.create_user = user
        address.update_user = user
        address.save()
        if tags is not None:
            address.tags.set(tags)
        return address
