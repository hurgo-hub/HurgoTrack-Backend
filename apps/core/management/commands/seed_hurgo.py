"""Datos base de Hurgo Track. Se puede ejecutar varias veces (idempotente).

    python manage.py seed_hurgo

Crea:
- Los tipos de adjunto de viaje que usa el código (remisión firmada, novedad, devolución, cargue).
- Los roles (grupos) con sus permisos de modelo.
- Un workflow por acción: primero ``validate.permission`` y luego el step de la app.
  El frontend los llama con POST /api/workflows/sync/<nombre>/.
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from enginedj.workflows.models import M_workflow

from apps.trips.models import M_trip_type_attach

APPS = ["companies", "locations", "fleet", "drivers", "orders", "trips", "apiOdoo"]

ATTACH_TYPES = [
    # key, nombre, es prueba de entrega
    ("delivery_proof", "Remisión firmada", True),
    ("novelty", "Foto de novedad", False),
    ("return", "Soporte de devolución", False),
    ("loading", "Foto de cargue", False),
]

ROLE_COMMERCIAL = "comercial"
ROLE_DISPATCH = "despacho"
ROLE_DRIVER = "conductor"
ROLE_ADMIN = "administracion"

# rol -> lista de "app_label.codename" | "app_label.*" (todos los de la app) | "app_label.view_m_*" (prefijo: solo los view estándar).
ROLE_PERMISSIONS = {
    ROLE_ADMIN: [f"{app}.*" for app in APPS],
    ROLE_DISPATCH: [
        *[f"{app}.view_m_*" for app in APPS],
        "trips.add_m_trip", "trips.change_m_trip",
        "trips.build_trip", "trips.register_series_trip", "trips.assign_trip", "trips.cancel_trip",
        "trips.create_return_trip", "trips.report_novelty_trip", "trips.view_all_trip",
        "orders.add_m_order", "orders.change_m_order", "orders.submit_order", "orders.cancel_order",
        "orders.confirm_order", "orders.cancel_confirmed_order", "orders.view_all_order",
        "orders.create_any_company_order",
    ],
    ROLE_COMMERCIAL: [
        "orders.view_m_order", "orders.add_m_order", "orders.change_m_order", "orders.submit_order",
        "orders.cancel_order", "orders.view_m_order_line", "orders.view_m_order_event",
        "orders.view_m_item", "orders.view_m_type_item", "orders.view_m_brand",
        "companies.view_m_company", "locations.view_m_*", "locations.add_m_address", "locations.change_m_address",
        "trips.view_m_trip", "trips.view_m_trip_line", "trips.view_m_trip_event", "trips.view_m_trip_attach",
    ],
    ROLE_DRIVER: [
        "trips.view_m_*", "trips.drive_trip", "trips.report_novelty_trip",
    ],
}

# workflow (= step) -> permisos que valida ``validate.permission`` antes del step.
# Los servicios vuelven a validar (y aplican reglas como "solo el conductor asignado").
WORKFLOWS = {
    # Pedidos (pasos 1 y 2)
    "orders.create": ["orders.add_m_order"],
    "orders.update": ["orders.change_m_order"],
    "orders.submit": ["orders.submit_order"],
    "orders.confirm": ["orders.confirm_order"],
    "orders.cancel": ["orders.view_m_order"],  # el servicio decide entre cancel_order y cancel_confirmed_order
    "orders.retrieve": ["orders.view_m_order"],
    "orders.list": ["orders.view_m_order"],
    "orders.items": ["orders.add_m_order"],
    "orders.pending_lines": ["trips.build_trip"],
    "companies.recipients": ["companies.view_m_company"],
    # Viajes (pasos 3 a 8)
    "trips.build": ["trips.build_trip"],
    "trips.add_allocations": ["trips.build_trip"],
    "trips.register_series": ["trips.register_series_trip"],
    "trips.assign": ["trips.assign_trip"],
    "trips.cancel": ["trips.cancel_trip"],
    "trips.create_return_trip": ["trips.create_return_trip"],
    "trips.mine": ["trips.drive_trip"],
    "trips.depart": ["trips.drive_trip"],
    "trips.start_delivery": ["trips.drive_trip"],
    "trips.deliver": ["trips.drive_trip"],
    "trips.register_return": ["trips.drive_trip"],
    "trips.report_novelty": ["trips.report_novelty_trip"],
    "trips.retrieve": ["trips.view_m_trip"],
    "trips.list": ["trips.view_m_trip"],
    # Flota
    "fleet.document_expirations": ["fleet.view_m_vehicle"],
    # Odoo
    "apiOdoo.get_purchase": ["orders.confirm_order"],
    "apiOdoo.get_create_partners": ["apiOdoo.sync_odoo"],
    "apiOdoo.get_create_products": ["apiOdoo.sync_odoo"],
    "apiOdoo.notify_delivery": ["apiOdoo.sync_odoo"],
}


def _permissions(spec: str):
    app_label, codename = spec.split(".", 1)
    qs = Permission.objects.filter(content_type__app_label=app_label)
    if codename == "*":
        return qs
    if codename.endswith("*"):
        return qs.filter(codename__startswith=codename[:-1])
    return qs.filter(codename=codename)


def workflow_config(step: str, permissions: list[str]) -> list[dict]:
    return [
        {"name": "validate.permission", "important": True, "params": {"permission_codenames": permissions}},
        {"name": step, "important": True},
    ]


class Command(BaseCommand):
    help = "Crea tipos de adjunto, roles con permisos y workflows de Hurgo Track."

    @transaction.atomic
    def handle(self, *args, **options):
        for key, name, is_proof in ATTACH_TYPES:
            M_trip_type_attach.objects.update_or_create(
                key=key, defaults={"name": name, "is_delivery_proof": is_proof, "is_active": True}
            )
        self.stdout.write(f"Tipos de adjunto: {len(ATTACH_TYPES)}")

        for role, specs in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = Permission.objects.none()
            for spec in specs:
                found = _permissions(spec)
                if not found.exists():
                    raise ValueError(f"Permiso inexistente en {role}: {spec}")
                perms |= found
            group.permissions.set(perms.distinct())
            self.stdout.write(f"Grupo {role}: {group.permissions.count()} permisos")

        for name, permissions in WORKFLOWS.items():
            for spec in permissions:
                if not _permissions(spec).exists():
                    raise ValueError(f"Permiso inexistente en el workflow {name}: {spec}")
            M_workflow.objects.update_or_create(
                name=name, defaults={"config": workflow_config(name, permissions), "is_active": True}
            )
        self.stdout.write(f"Workflows: {len(WORKFLOWS)}")
        self.stdout.write(self.style.SUCCESS("Datos base listos."))
