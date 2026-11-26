"""Permisos y workflows de la integración con Odoo. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["apiOdoo.*"],
    "despacho": ["apiOdoo.view_m_*"],
}

WORKFLOWS = {
    "apiOdoo.get_purchase": ["orders.confirm_order"],
    "apiOdoo.get_create_partners": ["apiOdoo.sync_odoo"],
    "apiOdoo.get_create_products": ["apiOdoo.sync_odoo"],
    "apiOdoo.notify_delivery": ["apiOdoo.sync_odoo"],
    # Odoo simulado: el facturador o despacho "compran" sin un Odoo real (ODOO_SIMULATED=True)
    "apiOdoo.mode": ["stock.view_m_purchase_request"],
    "apiOdoo.simulate_purchase": ["stock.view_m_purchase_request"],
}
