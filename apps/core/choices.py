"""Opciones compartidas entre apps."""

DOCUMENT_TYPE_CHOICES = [
    ("CC", "Cédula de ciudadanía"),
    ("CE", "Cédula de extranjería"),
    ("NIT", "NIT"),
    ("PP", "Pasaporte"),
    ("PPT", "Permiso por protección temporal"),
]

# Categorías de licencia de conducción en Colombia. Se usan en el conductor
# (su licencia) y en el vehículo (la que exige).
LICENSE_CATEGORY_CHOICES = [
    ("A1", "A1"), ("A2", "A2"),
    ("B1", "B1"), ("B2", "B2"), ("B3", "B3"),
    ("C1", "C1"), ("C2", "C2"), ("C3", "C3"),
]

# Qué categorías de vehículo puede manejar cada categoría de licencia.
# Una categoría superior incluye las inferiores de su grupo (y C incluye B).
LICENSE_COVERS = {
    "A1": {"A1"},
    "A2": {"A1", "A2"},
    "B1": {"B1"},
    "B2": {"B1", "B2"},
    "B3": {"B1", "B2", "B3"},
    "C1": {"B1", "C1"},
    "C2": {"B1", "B2", "C1", "C2"},
    "C3": {"B1", "B2", "B3", "C1", "C2", "C3"},
}


def license_covers(driver_category: str, vehicle_category: str) -> bool:
    """True si una licencia ``driver_category`` permite manejar un vehículo que exige ``vehicle_category``."""
    if not vehicle_category:
        return True
    return vehicle_category in LICENSE_COVERS.get(driver_category or "", set())
