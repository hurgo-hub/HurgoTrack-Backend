from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from enginedj.base.services import BaseService

from enginedj.base.exceptions import BusinessError, BusinessNotFound
from apps.fleet.entity import E_vehicle
from apps.fleet.repository import R_vehicle


class S_vehicle(BaseService[E_vehicle]):

    def __init__(self):
        super().__init__(repository=R_vehicle(), entity_class=E_vehicle)
        self.repository: R_vehicle = self.repository

    def get_for_trip(self, vehicle_id):
        vehicle = self.repository.get_for_update(vehicle_id)
        if vehicle is None:
            raise BusinessNotFound("El vehículo no existe.")
        if not vehicle.is_available:
            raise BusinessError(f"El vehículo {vehicle.plate} no está disponible.", code="vehicle_unavailable")
        return vehicle

    def check_documents(self, vehicle, today=None):
        """SOAT vigente siempre; revisión técnico-mecánica vigente salvo vehículo nuevo (modelo del año o del anterior)."""
        today = today or timezone.localdate()
        soat = self.repository.last_expire(vehicle, "soat")
        if soat is None or soat < today:
            raise BusinessError(f"El vehículo {vehicle.plate} no tiene SOAT vigente.", code="soat_expired")
        rtm = self.repository.last_expire(vehicle, "mechanical_inspection")
        is_new = vehicle.model_year is not None and today.year - vehicle.model_year <= 1
        if (rtm is None and not is_new) or (rtm is not None and rtm < today):
            raise BusinessError(f"El vehículo {vehicle.plate} no tiene revisión técnico-mecánica vigente.",
                                code="rtm_expired")

    def check_capacity(self, vehicle, weight, motorcycles):
        if vehicle.load_capacity_kg and weight > vehicle.load_capacity_kg:
            raise BusinessError(
                f"La carga ({weight} kg) supera la capacidad del vehículo ({vehicle.load_capacity_kg} kg).",
                code="over_capacity",
            )
        if vehicle.motorcycle_capacity and motorcycles > vehicle.motorcycle_capacity:
            raise BusinessError(
                f"El viaje lleva {motorcycles:.0f} motos y el vehículo carga {vehicle.motorcycle_capacity}.",
                code="over_capacity",
            )

    def document_expirations(self, days: int | None = None) -> dict:
        """SOAT, RTM y licencias vencidas, por vencer o faltantes (lo usa la tarea diaria de Celery)."""
        from apps.drivers.services import S_driver

        days = days if days is not None else settings.HURGO_EXPIRATION_WARNING_DAYS
        limit = timezone.localdate() + timedelta(days=days)
        result = {
            "until": limit.isoformat(),
            "soat": self.repository.expiring_documents("soat", limit),
            "mechanical_inspection": self.repository.expiring_documents("mechanical_inspection", limit),
            "driver_license": S_driver().expiring_licenses(limit),
        }
        for key in ("soat", "mechanical_inspection", "driver_license"):
            for row in result[key]:
                for field, value in row.items():
                    if hasattr(value, "isoformat"):
                        row[field] = value.isoformat()
        return result
