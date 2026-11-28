"""Permisos de conductores. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["drivers.*"],
    "despacho": ["drivers.view_m_*"],
}

WORKFLOWS = {
    # Conductores: los registra administración de Hurgo (con su usuario); despacho consulta
    "drivers.list": ["drivers.view_m_driver"],
    "drivers.save": ["drivers.view_m_driver"],
    # App del conductor: su celular para las notificaciones
    "mobile.device.register": ["trips.drive_trip"],
    "mobile.device.unregister": ["trips.drive_trip"],
}
