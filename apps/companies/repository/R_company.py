from django.db.models import Q

from enginedj.base.repository import BaseRepositoryImpl

from apps.companies.entity import E_company
from apps.companies.models import M_company


class R_company(BaseRepositoryImpl[E_company]):

    def __init__(self):
        super().__init__(model=M_company, entity_class=E_company)
        self.model: M_company = self.model

    def get_active(self, company_id) -> M_company | None:
        return self.model.objects.filter(pk=company_id, is_active=True).first()

    def recipients(self, query: str = "", limit: int = 50) -> list[M_company]:
        """Destinatarios activos con sus direcciones activas en ``active_addresses``."""
        from apps.locations.models import M_address

        qs = self.model.objects.filter(is_active=True, is_recipient=True)
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(document_number__icontains=query))
        companies = list(qs.order_by("name")[:limit])
        addresses = {}
        for address in M_address.objects.filter(
            is_active=True, company_id__in=[c.pk for c in companies]
        ).select_related("location_id").order_by("name"):
            addresses.setdefault(address.company_id_id, []).append(address)
        for company in companies:
            company.active_addresses = addresses.get(company.pk, [])
        return companies
