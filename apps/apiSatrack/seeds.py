"""Workflows de la integración con Satrack (mapa / GPS). Ver ``manage.py seed_workflows``.

La app no tiene modelos: usa los permisos de flota (posiciones de cualquier vehículo)
y de viajes (mapa de los viajes que el usuario ya puede ver).
"""

WORKFLOWS = {
    "apiSatrack.positions": ["fleet.view_m_vehicle"],
    "apiSatrack.history": ["fleet.view_m_vehicle"],
    "apiSatrack.map_overview": ["trips.view_m_trip"],
    "apiSatrack.trip_map": ["trips.view_m_trip"],
}
