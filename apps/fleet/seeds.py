"""Permisos y workflows de flota. Ver ``manage.py seed_workflows``."""

ROLES = {
    "administracion": ["fleet.*"],
    "despacho": ["fleet.view_m_*"],
}

WORKFLOWS = {
    "fleet.document_expirations": ["fleet.view_m_vehicle"],
    "fleet.documents": ["fleet.view_m_vehicle"],
    "fleet.document.upload": ["fleet.add_m_vehicle_document"],
    # Vehículos, propietarios, SOAT y RTM: los registra administración de Hurgo; despacho consulta
    "fleet.lookups": ["fleet.view_m_vehicle"],
    "fleet.vehicles": ["fleet.view_m_vehicle"],
    "fleet.vehicle.save": ["fleet.view_m_vehicle"],
    "fleet.partners": ["fleet.view_m_partner"],
    "fleet.partner.save": ["fleet.view_m_partner"],
    "fleet.soat.save": ["fleet.add_m_soat"],
    "fleet.rtm.save": ["fleet.add_m_mechanical_inspection"],
}
