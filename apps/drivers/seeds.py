"""Permisos de conductores. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["drivers.*"],
    "despacho": ["drivers.view_m_*"],
}
