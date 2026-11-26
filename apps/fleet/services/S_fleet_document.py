"""Documentos de flota que exige Hurgo (vehículo y conductor), con vencimiento."""

from django.db import transaction
from django.utils import timezone

from enginedj.base.exceptions import BusinessError, BusinessNotFound
from enginedj.base.services.permissions import require_perm

from apps.companies.uploads import display_name
from apps.fleet.models import M_driver_document, M_fleet_document_type, M_vehicle, M_vehicle_document

PERM = "fleet.add_m_vehicle_document"


def _target(vehicle_id=None, driver_id=None):
    from apps.drivers.models import M_driver

    if vehicle_id:
        owner = M_vehicle.objects.filter(pk=vehicle_id).first()
        return "vehicle", owner, M_vehicle_document, "vehicle_id"
    owner = M_driver.objects.filter(pk=driver_id).first() if driver_id else None
    return "driver", owner, M_driver_document, "driver_id"


class S_fleet_document:

    def documents(self, user, *, vehicle_id=None, driver_id=None):
        require_perm(user, "fleet.view_m_vehicle", "No tienes permiso para ver la flota.")
        applies_to, owner, model, field = _target(vehicle_id, driver_id)
        if owner is None:
            raise BusinessNotFound("El vehículo o conductor no existe.")
        today = timezone.localdate()
        docs = {}
        for d in model.objects.filter(**{field: owner}, is_active=True).order_by("-date_expire", "-id"):
            docs.setdefault(d.type_id_id, []).append(
                {"id": d.id, "name": display_name(d.file), "date_expire": d.date_expire,
                 "valid": d.date_expire is None or d.date_expire >= today})
        return [
            {"id": t.id, "name": t.name, "is_required": t.is_required, "has_expiration": t.has_expiration,
             "files": docs.get(t.id, []),
             "ok": any(f["valid"] or not t.has_expiration for f in docs.get(t.id, []))}
            for t in M_fleet_document_type.objects.filter(applies_to=applies_to, is_active=True).order_by("name")
        ]

    @transaction.atomic
    def upload(self, user, *, type_id, files, date_expire=None, vehicle_id=None, driver_id=None):
        require_perm(user, PERM, "Solo administración sube documentos de flota.")
        applies_to, owner, model, field = _target(vehicle_id, driver_id)
        if owner is None:
            raise BusinessNotFound("El vehículo o conductor no existe.")
        doc_type = M_fleet_document_type.objects.filter(pk=type_id, applies_to=applies_to, is_active=True).first()
        if doc_type is None:
            raise BusinessNotFound("El tipo de documento no existe o no aplica.")
        if doc_type.has_expiration and not date_expire:
            raise BusinessError(f"{doc_type.name} lleva fecha de vencimiento.", code="expiration_required")
        if not files:
            raise BusinessError("Adjunta el archivo.")
        for file in files:
            model.objects.create(**{field: owner}, type_id=doc_type, file=file, date_expire=date_expire,
                                 create_user=user)
        return self.documents(user, vehicle_id=vehicle_id, driver_id=driver_id)
