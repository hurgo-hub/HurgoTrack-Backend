from django.db import transaction

from enginedj.base.services import BaseService

from apps.core.exceptions import BusinessError, BusinessNotFound
from apps.core.permissions import require_perm
from apps.orders.repository import R_order_line_trip
from apps.trips.entity import E_trip_line_serie
from apps.trips.repository import R_trip, R_trip_line, R_trip_line_serie


class S_trip_line_serie(BaseService[E_trip_line_serie]):

    def __init__(self):
        super().__init__(repository=R_trip_line_serie(), entity_class=E_trip_line_serie)
        self.repository: R_trip_line_serie = self.repository

    @transaction.atomic
    def register_series(self, user, trip_id, trip_line_id, series):
        """Las motos se registran una por una con su VIN: [{"order_line_trip_id", "vin", "engine_number"}]."""
        require_perm(user, "trips.register_series_trip", "Solo el equipo de despacho registra VIN.")
        trip = R_trip().get_for_update(trip_id)
        if trip is None:
            raise BusinessNotFound("El viaje no existe.")
        if trip.state not in ("draft", "assigned"):
            raise BusinessError(f"No se pueden registrar VIN: el viaje {trip.code} está "
                                f"'{trip.get_state_display()}'.", code="invalid_state")
        stop = R_trip_line().get_for_update(trip, trip_line_id)
        if stop is None:
            raise BusinessNotFound("La parada no pertenece a este viaje.")

        r_allocation = R_order_line_trip()
        created = []
        for row in series:
            vin = str(row["vin"]).strip().upper().replace(" ", "")
            if not vin:
                raise BusinessError("El VIN no puede estar vacío.")
            allocation = r_allocation.get_in_stop(row["order_line_trip_id"], stop)
            if allocation is None:
                raise BusinessNotFound("La línea de pedido no va en esta parada.")
            item = allocation.order_line_id.item_id
            if not item.is_serialized:
                raise BusinessError(f"{item} no se despacha por número de serie.")
            if self.repository.registered_count(allocation) >= allocation.qty:
                raise BusinessError(f"Ya están registradas las {allocation.qty:.0f} unidades de {item} en esta parada.")
            in_use = self.repository.vin_in_delivery_trip(vin)
            if in_use is not None:
                raise BusinessError(f"El VIN {vin} ya está en el viaje {in_use.trip_line_id.trip_id.code}.",
                                    code="vin_in_use")
            created.append(self.repository.create_serie(
                trip_line_id=stop, order_line_trip_id=allocation, vin=vin,
                engine_number=str(row.get("engine_number") or "").strip().upper(), create_user_id=user,
            ))
        return created
