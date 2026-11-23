from enginedj.base.repository import BaseRepositoryImpl

from apps.locations.entity import E_address
from apps.locations.models import M_address


class R_address(BaseRepositoryImpl[E_address]):

    def __init__(self):
        super().__init__(model=M_address, entity_class=E_address)
        self.model: M_address = self.model

    def get_active(self, address_id) -> M_address | None:
        return self.model.objects.filter(pk=address_id, is_active=True).first()
