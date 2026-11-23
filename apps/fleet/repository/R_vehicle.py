from django.db.models import Max, Q

from enginedj.base.repository import BaseRepositoryImpl

from apps.fleet.entity import E_vehicle
from apps.fleet.models import M_vehicle


class R_vehicle(BaseRepositoryImpl[E_vehicle]):

    def __init__(self):
        super().__init__(model=M_vehicle, entity_class=E_vehicle)
        self.model: M_vehicle = self.model

    def get_for_update(self, vehicle_id) -> M_vehicle | None:
        return self.model.objects.select_for_update().filter(pk=vehicle_id, is_active=True).first()

    @staticmethod
    def last_expire(vehicle: M_vehicle, relation: str):
        """Fecha de vencimiento del documento vigente más reciente (soat / mechanical_inspection)."""
        related = getattr(vehicle, f"{relation}_vehicle_id")
        return related.filter(is_active=True).aggregate(m=Max("date_expire"))["m"]

    def expiring_documents(self, relation: str, limit_date) -> list[dict]:
        """Vehículos activos cuyo documento más reciente vence antes de ``limit_date`` o que no lo tienen."""
        lookup = f"{relation}_vehicle_id"
        return list(
            self.model.objects.filter(is_active=True)
            .annotate(last_expire=Max(f"{lookup}__date_expire", filter=Q(**{f"{lookup}__is_active": True})))
            .filter(Q(last_expire__lte=limit_date) | Q(last_expire__isnull=True))
            .order_by("last_expire")
            .values("id", "plate", "last_expire")
        )
