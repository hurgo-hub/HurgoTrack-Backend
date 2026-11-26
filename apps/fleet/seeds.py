"""Permisos y workflows de flota. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["fleet.*"],
    "despacho": ["fleet.view_m_*"],
}

WORKFLOWS = {
    "fleet.document_expirations": ["fleet.view_m_vehicle"],
    "fleet.documents": ["fleet.view_m_vehicle"],
    "fleet.document.upload": ["fleet.add_m_vehicle_document"],
}
