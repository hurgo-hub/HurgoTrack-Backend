from enginedj.base.repository import BaseRepositoryImpl

from apps.apiOdoo.entity import E_odoo_sync_log
from apps.apiOdoo.models import M_odoo_sync_log


class R_odoo_sync_log(BaseRepositoryImpl[E_odoo_sync_log]):

    def __init__(self):
        super().__init__(model=M_odoo_sync_log, entity_class=E_odoo_sync_log)
        self.model: M_odoo_sync_log = self.model

    def register(self, operation, status, odoo_model="", reference="", request=None, response=None, error="",
                 user=None) -> M_odoo_sync_log:
        return self.model.objects.create(
            operation=operation, status=status, odoo_model=odoo_model, reference=str(reference or "")[:120],
            request=request or {}, response=response, error=error or "", create_user=user,
        )
