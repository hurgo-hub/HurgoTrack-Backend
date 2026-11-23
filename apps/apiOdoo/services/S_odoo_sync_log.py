from enginedj.base.services import BaseService

from apps.apiOdoo.entity import E_odoo_sync_log
from apps.apiOdoo.repository import R_odoo_sync_log


class S_odoo_sync_log(BaseService[E_odoo_sync_log]):

    def __init__(self):
        super().__init__(repository=R_odoo_sync_log(), entity_class=E_odoo_sync_log)
        self.repository: R_odoo_sync_log = self.repository

    def success(self, operation, response=None, **kwargs):
        response = response if isinstance(response, (dict, list)) or response is None else {"result": response}
        return self.repository.register(operation, "success", response=response, **kwargs)

    def error(self, operation, exc, **kwargs):
        return self.repository.register(operation, "error", error=str(exc), **kwargs)
