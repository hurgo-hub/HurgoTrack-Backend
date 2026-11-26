"""Gestión de la flota desde la app: vehículos, propietarios, SOAT y revisión técnico-mecánica.

La flota es de la empresa Hurgo (transportador; la crea ``companies/seeds.py`` con los datos del
.env) y solo la gestiona el equipo de Hurgo: administración registra y edita, despacho consulta.
"""

from django.conf import settings
from django.db import transaction

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.models import M_company
from enginedj.base.services.permissions import require_perm

from apps.companies.tenancy import is_hurgo
from apps.fleet.models import (
    M_bodywork, M_brand_vehicle, M_mechanical_inspection, M_partner, M_soat, M_transit, M_type_vehicle, M_vehicle,
)


def hurgo_company() -> M_company:
    """La empresa Hurgo: transportador propio (no cliente, no independiente)."""
    carriers = M_company.objects.filter(is_carrier=True, is_freelance=False, is_client=False, is_active=True)
    nit = (settings.HURGO_COMPANY_NIT or "").strip()
    company = (carriers.filter(document_number=nit).first() if nit else None) or carriers.order_by("pk").first()
    if company is None:
        raise BusinessError("Falta la empresa Hurgo: configura HURGO_COMPANY_NAME y HURGO_COMPANY_NIT en el .env "
                            "del servidor y corre seed_workflows.", code="missing_hurgo_company")
    return company


def require_fleet(user, perm, message):
    require_perm(user, perm, message)
    if not is_hurgo(user):
        raise BusinessPermissionError("La flota la gestiona Hurgo.")


def _set(obj, data, fields):
    for field in fields:
        if field in data:
            value = data[field]
            setattr(obj, field, value.strip() if isinstance(value, str) else value)


VEHICLE_FIELDS = ("model_year", "color", "load_capacity_kg", "empty_weight_kg", "motorcycle_capacity", "vin",
                  "fuel_type", "license_category", "transmission", "is_available", "is_active")
PARTNER_FIELDS = ("name", "is_company", "document_type", "email", "phone", "address", "is_active")


class S_fleet:

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    def lookups(self, user):
        require_fleet(user, "fleet.view_m_vehicle", "No tienes permiso para ver la flota.")

        def rows(model):
            return [{"id": r.id, "name": r.name} for r in model.objects.filter(is_active=True).order_by("name")]

        return {
            "type_vehicles": rows(M_type_vehicle),
            "brand_vehicles": rows(M_brand_vehicle),
            "bodyworks": rows(M_bodywork),
            "transits": rows(M_transit),
            "partners": [{"id": p.id, "name": p.name, "document_number": p.document_number}
                         for p in M_partner.objects.filter(is_active=True).order_by("name")],
        }

    @staticmethod
    def _with_documents():
        return (M_vehicle.objects.select_related("type_vehicle_id", "brand_vehicle_id", "owner_id")
                .prefetch_related("soat_vehicle_id", "mechanical_inspection_vehicle_id"))

    def vehicles(self, user):
        require_fleet(user, "fleet.view_m_vehicle", "No tienes permiso para ver la flota.")
        return list(self._with_documents().order_by("-is_active", "plate"))

    def vehicle_detail(self, vehicle_id) -> M_vehicle:
        return self._with_documents().get(pk=vehicle_id)

    def partners(self, user):
        require_fleet(user, "fleet.view_m_partner", "No tienes permiso para ver los propietarios.")
        return list(M_partner.objects.order_by("-is_active", "name"))

    # ------------------------------------------------------------------
    # Vehículos
    # ------------------------------------------------------------------
    @staticmethod
    def _active(model, pk, label):
        obj = model.objects.filter(pk=pk, is_active=True).first() if pk else None
        if obj is None:
            raise BusinessNotFound(f"{label} no existe o está inactivo.")
        return obj

    @transaction.atomic
    def save_vehicle(self, user, data: dict) -> M_vehicle:
        """Crea (sin vehicle_id) o edita un vehículo de la flota de Hurgo."""
        if data.get("vehicle_id"):
            require_fleet(user, "fleet.change_m_vehicle", "No tienes permiso para editar vehículos.")
            vehicle = M_vehicle.objects.select_for_update().filter(pk=data["vehicle_id"]).first()
            if vehicle is None:
                raise BusinessNotFound("El vehículo no existe.")
            vehicle.update_user = user
        else:
            require_fleet(user, "fleet.add_m_vehicle", "No tienes permiso para registrar vehículos.")
            missing = [label for field, label in (("plate", "placa"), ("type_vehicle_id", "tipo"),
                                                  ("brand_vehicle_id", "marca"), ("owner_id", "propietario"))
                       if not data.get(field)]
            if missing:
                raise BusinessError(f"Falta: {', '.join(missing)}.", code="invalid_input")
            vehicle = M_vehicle(company_id=hurgo_company(), create_user=user)
        if "plate" in data:
            plate = "".join(ch for ch in data["plate"].upper() if ch.isalnum())
            if not plate:
                raise BusinessError("Indica la placa.")
            if M_vehicle.objects.filter(plate=plate).exclude(pk=vehicle.pk).exists():
                raise BusinessError(f"Ya existe un vehículo con la placa {plate}.", code="duplicate_plate")
            vehicle.plate = plate
        for field, model, label in (("type_vehicle_id", M_type_vehicle, "El tipo de vehículo"),
                                    ("brand_vehicle_id", M_brand_vehicle, "La marca"),
                                    ("owner_id", M_partner, "El propietario")):
            if data.get(field):
                setattr(vehicle, field, self._active(model, data[field], label))
        for field, model, label in (("holder_id", M_partner, "El tenedor"), ("bodywork_id", M_bodywork, "La carrocería"),
                                    ("transit_id", M_transit, "El organismo de tránsito")):
            if field in data:
                setattr(vehicle, field, self._active(model, data[field], label) if data[field] else None)
        _set(vehicle, data, VEHICLE_FIELDS)
        vehicle.save()
        return vehicle

    # ------------------------------------------------------------------
    # Propietarios (terceros)
    # ------------------------------------------------------------------
    @transaction.atomic
    def save_partner(self, user, data: dict) -> M_partner:
        company = hurgo_company()
        if data.get("partner_id"):
            require_fleet(user, "fleet.change_m_partner", "No tienes permiso para editar propietarios.")
            partner = M_partner.objects.select_for_update().filter(pk=data["partner_id"]).first()
            if partner is None:
                raise BusinessNotFound("El propietario no existe.")
            partner.update_user = user
        else:
            require_fleet(user, "fleet.add_m_partner", "No tienes permiso para registrar propietarios.")
            if not (data.get("name") or "").strip() or not (data.get("document_number") or "").strip():
                raise BusinessError("Indica nombre y documento del propietario.", code="invalid_input")
            partner = M_partner(company_id=company, create_user=user)
        if "document_number" in data:
            number = "".join(ch for ch in data["document_number"].upper() if ch.isalnum())
            if M_partner.objects.filter(company_id=partner.company_id_id or company.pk,
                                        document_number=number).exclude(pk=partner.pk).exists():
                raise BusinessError(f"Ya existe un propietario con el documento {number}.", code="duplicate_partner")
            partner.document_number = number
        _set(partner, data, PARTNER_FIELDS)
        partner.save()
        return partner

    # ------------------------------------------------------------------
    # SOAT y revisión técnico-mecánica (cada registro nuevo es una renovación)
    # ------------------------------------------------------------------
    @transaction.atomic
    def add_soat(self, user, data: dict, file=None) -> M_soat:
        require_fleet(user, "fleet.add_m_soat", "No tienes permiso para registrar el SOAT.")
        vehicle = self._active(M_vehicle, data["vehicle_id"], "El vehículo")
        return M_soat.objects.create(
            vehicle_id=vehicle, insurer_name=data["insurer_name"].strip(), policy_number=data["policy_number"].strip(),
            date_start=data.get("date_start"), date_expire=data["date_expire"], file=file, create_user=user,
        )

    @transaction.atomic
    def add_rtm(self, user, data: dict, file=None) -> M_mechanical_inspection:
        require_fleet(user, "fleet.add_m_mechanical_inspection",
                      "No tienes permiso para registrar la revisión técnico-mecánica.")
        vehicle = self._active(M_vehicle, data["vehicle_id"], "El vehículo")
        return M_mechanical_inspection.objects.create(
            vehicle_id=vehicle, certificate_number=data["certificate_number"].strip(),
            cda_name=data["cda_name"].strip(), date_expedition=data["date_expedition"],
            date_expire=data["date_expire"], file=file, create_user=user,
        )
