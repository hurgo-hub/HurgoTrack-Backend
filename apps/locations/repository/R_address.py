from django.db.models import Q

from enginedj.base.repository import BaseRepositoryImpl

from apps.locations.entity import E_address
from apps.locations.models import M_address
from enginedj.base.models import M_company


class R_address(BaseRepositoryImpl[E_address]):

    def __init__(self):
        super().__init__(model=M_address, entity_class=E_address)
        self.model: M_address = self.model

    def get_active(self, address_id) -> M_address | None:
        return self.model.objects.filter(pk=address_id, is_active=True).first()

    def recipients(self, query: str = "", limit: int = 50) -> list[M_company]:
        """Empresas destinatarias activas con sus direcciones activas en ``active_addresses``."""
        qs = M_company.objects.filter(is_active=True, is_recipient=True)
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(document_number__icontains=query))
        companies = list(qs.order_by("name")[:limit])
        addresses = {}
        for address in self.model.objects.filter(
            is_active=True, company_id__in=[c.pk for c in companies]
        ).select_related("location_id").order_by("name"):
            addresses.setdefault(address.company_id_id, []).append(address)
        for company in companies:
            company.active_addresses = addresses.get(company.pk, [])
        return companies
