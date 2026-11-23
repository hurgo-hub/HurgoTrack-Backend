from django.utils import timezone

from enginedj.base.services import BaseService

from enginedj.base.choices import license_covers
from enginedj.base.exceptions import BusinessError, BusinessNotFound
from apps.drivers.entity import E_driver
from apps.drivers.repository import R_driver


class S_driver(BaseService[E_driver]):

    def __init__(self):
        super().__init__(repository=R_driver(), entity_class=E_driver)
        self.repository: R_driver = self.repository

    def get_for_trip(self, driver_id):
        driver = self.repository.get_for_update(driver_id)
        if driver is None:
            raise BusinessNotFound("El conductor no existe.")
        if not driver.is_available:
            raise BusinessError(f"El conductor {driver} no está disponible.", code="driver_unavailable")
        return driver

    def check_can_drive(self, driver, vehicle, today=None):
        """La licencia cubre la categoría del vehículo y está vigente."""
        today = today or timezone.localdate()
        if not license_covers(driver.license_category, vehicle.license_category):
            raise BusinessError(
                f"La licencia {driver.license_category} no permite manejar un vehículo {vehicle.license_category}.",
                code="license_category",
            )
        if driver.license_expire and driver.license_expire < today:
            raise BusinessError(f"La licencia de {driver} venció el {driver.license_expire}.", code="license_expired")

    def is_user(self, driver_id, user) -> bool:
        return self.repository.is_user(driver_id, user)

    def get_by_user(self, user):
        return self.repository.get_by_user(user)

    def refresh_rating(self, driver_id):
        self.repository.refresh_rating(driver_id)

    def expiring_licenses(self, limit_date):
        return self.repository.expiring_licenses(limit_date)
