from decimal import Decimal

from django.db.models import Avg

from enginedj.base.repository import BaseRepositoryImpl

from apps.drivers.entity import E_driver
from apps.drivers.models import M_driver


class R_driver(BaseRepositoryImpl[E_driver]):

    def __init__(self):
        super().__init__(model=M_driver, entity_class=E_driver)
        self.model: M_driver = self.model

    def get_for_update(self, driver_id) -> M_driver | None:
        return self.model.objects.select_for_update().filter(pk=driver_id, is_active=True).first()

    def is_user(self, driver_id, user) -> bool:
        return driver_id is not None and self.model.objects.filter(pk=driver_id, user_id=user).exists()

    def get_by_user(self, user) -> M_driver | None:
        return self.model.objects.filter(user_id=user, is_active=True).first()

    def refresh_rating(self, driver_id):
        """Promedio de las calificaciones de sus entregas."""
        from apps.trips.models import M_trip_line

        average = M_trip_line.objects.filter(
            trip_id__driver_id=driver_id, rating__isnull=False, state="delivered"
        ).aggregate(a=Avg("rating"))["a"]
        self.model.objects.filter(pk=driver_id).update(
            average_rating=Decimal(str(round(average, 2))) if average is not None else Decimal("0")
        )
        self._invalidate_list_cache()

    def expiring_licenses(self, limit_date) -> list[dict]:
        return list(
            self.model.objects.filter(is_active=True, license_expire__lte=limit_date)
            .order_by("license_expire")
            .values("id", "license_number", "license_expire")
        )
