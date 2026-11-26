import logging

from enginedj.base.services import BaseService

from apps.apiOdoo.entity import E_odoo_sync_log
from apps.apiOdoo.repository import R_odoo_sync_log

logger = logging.getLogger(__name__)


class S_odoo_sync_log(BaseService[E_odoo_sync_log]):

    def __init__(self):
        super().__init__(repository=R_odoo_sync_log(), entity_class=E_odoo_sync_log)
        self.repository: R_odoo_sync_log = self.repository

    # La bitácora vive en el esquema de cada empresa. Lo que corre en el central (ej. sincronizar
    # empresas desde Odoo) va al log de la aplicación.
    @staticmethod
    def _in_company_schema() -> bool:
        from django.db import connection

        return getattr(connection, "schema_name", "public") != "public"

    def success(self, operation, response=None, **kwargs):
        if not self._in_company_schema():
            logger.info("Odoo %s: ok %s", operation, kwargs.get("reference", ""))
            return None
        response = response if isinstance(response, (dict, list)) or response is None else {"result": response}
        return self.repository.register(operation, "success", response=response, **kwargs)

    def error(self, operation, exc, **kwargs):
        if not self._in_company_schema():
            logger.warning("Odoo %s: error %s", operation, exc)
            return None
        return self.repository.register(operation, "error", error=str(exc), **kwargs)
