"""Operaciones de Odoo que usa Hurgo Track (igual que ApiSintesisService en arquitecturabase)."""

from apps.apiOdoo.repository import ApiOdooRepository

PURCHASE_FIELDS = ["id", "name", "state", "partner_id", "date_order", "amount_total", "order_line"]
PARTNER_FIELDS = ["id", "name", "vat", "email", "phone", "is_company"]
PRODUCT_FIELDS = ["id", "name", "default_code", "weight"]
PURCHASE_LINE_FIELDS = ["id", "order_id", "product_id", "name", "product_qty", "qty_received", "product_uom"]


class ApiOdooService:

    def __init__(self, force_cache: bool = False):
        self.repository = ApiOdooRepository(force_cache=force_cache)

    def get_purchase(self, name: str) -> dict | None:
        """Compra (purchase.order) por su referencia, ej. P00012."""
        result = self.repository.search_read("purchase.order", [["name", "=", name]], PURCHASE_FIELDS, limit=1)
        return result[0] if result else None

    def get_purchase_lines(self, purchase_odoo_id: int) -> list[dict]:
        """Líneas (purchase.order.line) de una compra: producto y cantidad comprada / recibida."""
        return self.repository.search_read("purchase.order.line", [["order_id", "=", purchase_odoo_id]],
                                           PURCHASE_LINE_FIELDS, order="id")

    def get_partners(self, domain: list | None = None, limit: int | None = None) -> list[dict]:
        """Contactos (res.partner). Por defecto solo empresas."""
        return self.repository.search_read("res.partner", domain or [["is_company", "=", True]], PARTNER_FIELDS,
                                           limit=limit, order="id")

    def get_products(self, domain: list | None = None, limit: int | None = None) -> list[dict]:
        """Productos (product.product)."""
        return self.repository.search_read("product.product", domain or [], PRODUCT_FIELDS, limit=limit, order="id")

    def post_message(self, model: str, res_id: int, body: str):
        """Deja una nota en el chatter del registro de Odoo."""
        return self.repository.message_post(model, res_id, body)
