"""Permisos de conductores. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["drivers.*"],
    "despacho": ["drivers.view_m_*"],
}

WORKFLOWS = {
    # Conductores: los registra administración de Hurgo (con su usuario); despacho consulta
    "drivers.list": ["drivers.view_m_driver"],
    "drivers.save": ["drivers.view_m_driver"],
}
