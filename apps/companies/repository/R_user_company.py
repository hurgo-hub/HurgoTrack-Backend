from enginedj.base.repository import BaseRepositoryImpl

from apps.companies.entity import E_user_company
from apps.companies.models import M_user_company


class R_user_company(BaseRepositoryImpl[E_user_company]):

    def __init__(self):
        super().__init__(model=M_user_company, entity_class=E_user_company)
        self.model: M_user_company = self.model

    def company_ids_for(self, user) -> list[int]:
        return list(
            self.model.objects.filter(user_id=user, is_active=True, company_id__is_active=True).values_list(
                "company_id", flat=True
            )
        )
