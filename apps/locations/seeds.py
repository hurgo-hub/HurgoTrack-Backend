"""Permisos de empresas (base del motor) y direcciones. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["base.*", "locations.*"],
    "despacho": ["base.view_m_*", "locations.view_m_*"],
    "comercial": ["base.view_m_company", "locations.view_m_*", "locations.add_m_address", "locations.change_m_address"],
}

WORKFLOWS = {
    "locations.recipients": ["locations.view_m_address"],
}
