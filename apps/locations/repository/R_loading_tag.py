from enginedj.base.repository import BaseRepositoryImpl

from apps.locations.entity import E_loading_tag
from apps.locations.models import M_loading_tag


class R_loading_tag(BaseRepositoryImpl[E_loading_tag]):

    def __init__(self):
        super().__init__(model=M_loading_tag, entity_class=E_loading_tag)
        self.model: M_loading_tag = self.model

    def active(self, query: str = "") -> list[M_loading_tag]:
        qs = self.model.objects.filter(is_active=True)
        if query:
            qs = qs.filter(name__icontains=query)
        return list(qs.order_by("name"))

    def active_by_ids(self, tag_ids) -> dict[int, M_loading_tag]:
        return {tag.pk: tag for tag in self.model.objects.filter(pk__in=tag_ids, is_active=True)}

    def get_by_name(self, name: str) -> M_loading_tag | None:
        return self.model.objects.filter(name__iexact=name).first()

    def create_tag(self, name: str, user) -> M_loading_tag:
        return self.model.objects.create(name=name, create_user=user)
