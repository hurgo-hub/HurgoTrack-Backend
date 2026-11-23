from django.conf import settings

from enginedj.base.services import BaseService

from apps.apiOdoo.entity import E_odoo_purchase
from apps.apiOdoo.repository import R_odoo_purchase
from apps.apiOdoo.services.apiService import ApiOdooService
from apps.apiOdoo.services.S_odoo_sync_log import S_odoo_sync_log
from enginedj.base.exceptions import BusinessError


class S_odoo_purchase(BaseService[E_odoo_purchase]):

    def __init__(self):
        super().__init__(repository=R_odoo_purchase(), entity_class=E_odoo_purchase)
        self.repository: R_odoo_purchase = self.repository

    def sync_by_name(self, name: str, user=None):
        """Trae la compra de Odoo, actualiza la copia local y la devuelve."""
        name = (name or "").strip()
        log = S_odoo_sync_log()
        try:
            data = ApiOdooService().get_purchase(name)
        except Exception as exc:
            log.error("get_purchase", exc, odoo_model="purchase.order", reference=name, user=user)
            raise
        log.success("get_purchase", data, odoo_model="purchase.order", reference=name, user=user)
        if data is None:
            raise BusinessError(f"La compra {name} no existe en Odoo.", code="odoo_purchase_not_found")
        return self.repository.upsert_from_odoo(data, user)

    def validate_for_order(self, name: str, order, user=None):
        """Paso 2: la compra debe existir en Odoo y estar confirmada para confirmar el pedido."""
        purchase = self.sync_by_name(name, user)
        if purchase.state not in settings.ODOO_CONFIRMED_PURCHASE_STATES:
            raise BusinessError(
                f"La compra {purchase.name} está en estado '{purchase.state}' en Odoo; debe estar confirmada.",
                code="odoo_purchase_not_confirmed",
            )
        return purchase

    def get_or_sync(self, name: str, user=None):
        return self.repository.get_by_name(name) or self.sync_by_name(name, user)
