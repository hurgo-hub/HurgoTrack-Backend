"""Tipos de adjunto, permisos y workflows de viajes (pasos 3 a 8). Ver ``manage.py seed_workflows``."""

ATTACH_TYPES = [
    # key, nombre, es prueba de entrega
    ("delivery_proof", "Remisión firmada", True),
    ("novelty", "Foto de novedad", False),
    ("return", "Soporte de devolución", False),
    ("loading", "Foto de cargue", False),
]

ROLES = {
    "administracion": ["trips.*"],
    "despacho": [
        "trips.view_m_*",
        "trips.add_m_trip", "trips.change_m_trip",
        "trips.build_trip", "trips.register_series_trip", "trips.assign_trip", "trips.cancel_trip",
        "trips.create_return_trip", "trips.report_novelty_trip", "trips.view_all_trip",
    ],
    "comercial": ["trips.view_m_trip", "trips.view_m_trip_line", "trips.view_m_trip_event", "trips.view_m_trip_attach"],
    "admin_empresa": ["trips.view_m_trip", "trips.view_m_trip_line", "trips.view_m_trip_event",
                      "trips.view_m_trip_attach"],
    # view_m_* y no view_*: view_all_trip le dejaría ver todos los viajes.
    "conductor": ["trips.view_m_*", "trips.drive_trip", "trips.report_novelty_trip"],
}

WORKFLOWS = {
    "trips.build": ["trips.build_trip"],
    "trips.add_allocations": ["trips.build_trip"],
    "trips.register_series": ["trips.register_series_trip"],
    "trips.assign": ["trips.assign_trip"],
    "trips.resources": ["trips.assign_trip"],
    "trips.cancel": ["trips.cancel_trip"],
    "trips.create_return_trip": ["trips.create_return_trip"],
    "trips.mine": ["trips.drive_trip"],
    "trips.depart": ["trips.drive_trip"],
    "trips.start_delivery": ["trips.drive_trip"],
    "trips.deliver": ["trips.drive_trip"],  # el servicio exige además ser el conductor asignado
    "trips.register_return": ["trips.drive_trip"],
    "trips.report_novelty": ["trips.report_novelty_trip"],
    "trips.retrieve": ["trips.view_m_trip"],
    "trips.list": ["trips.view_m_trip"],
}


def seed(stdout):
    from apps.trips.models import M_trip_type_attach

    for key, name, is_proof in ATTACH_TYPES:
        M_trip_type_attach.objects.update_or_create(
            key=key, defaults={"name": name, "is_delivery_proof": is_proof, "is_active": True}
        )
    stdout.write(f"Tipos de adjunto de viaje: {len(ATTACH_TYPES)}")
