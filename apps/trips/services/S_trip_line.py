"""Reglas de las paradas (pasos 5 y 7 del documento): reparto, entrega y devolución. Solo el conductor asignado."""

from django.db import transaction
from django.utils import timezone

from enginedj.base.services import BaseService

from apps.core.exceptions import BusinessError, BusinessNotFound
from apps.orders.repository import R_order_line_trip
from apps.orders.services import S_order_line
from apps.trips.entity import E_trip_line
from apps.trips.repository import R_trip_line, R_trip_line_serie
from apps.trips.services.S_trip import ON_ROUTE_STATES, S_trip
from apps.trips.services.S_trip_attach import S_trip_attach

OPEN_STOP_STATES = ("in_route", "delivering")


class S_trip_line(BaseService[E_trip_line]):

    def __init__(self):
        super().__init__(repository=R_trip_line(), entity_class=E_trip_line)
        self.repository: R_trip_line = self.repository
        self.s_trip = S_trip()

    def _open_stop(self, user, trip_id, trip_line_id, action):
        trip = self.s_trip.lock(trip_id)
        self.s_trip.require_driver(trip, user)
        self.s_trip.require_state(trip, ON_ROUTE_STATES, action)
        stop = self.repository.get_for_update(trip, trip_line_id)
        if stop is None:
            raise BusinessNotFound("La parada no pertenece a este viaje.")
        return trip, stop

    @staticmethod
    def _require_open(stop):
        if stop.state not in OPEN_STOP_STATES:
            raise BusinessError(f"La parada {stop.sequence} ya está '{stop.get_state_display()}'.", code="invalid_state")

    def _after_stop_finished(self, trip, stop, user):
        S_order_line().refresh(R_order_line_trip().order_line_ids_of_stop(stop), user)
        self.s_trip.close_if_done(trip, user)

    @transaction.atomic
    def start_delivery(self, user, trip_id, trip_line_id, *, latitude=None, longitude=None):
        """Paso 5: el conductor llega a la parada y empieza el reparto."""
        trip, stop = self._open_stop(user, trip_id, trip_line_id, "iniciar reparto")
        if stop.state != "in_route":
            raise BusinessError(f"La parada {stop.sequence} está '{stop.get_state_display()}'.", code="invalid_state")
        stop.state = "delivering"
        self.repository.save_stop(stop, user)
        if trip.state == "in_route":
            self.s_trip.set_state(trip, user, "delivering", "En reparto", line=stop, latitude=latitude,
                                  longitude=longitude)
        else:
            self.s_trip.events.register(trip, user, f"En reparto parada {stop.sequence}", line=stop,
                                        from_state="in_route", to_state="delivering",
                                        latitude=latitude, longitude=longitude)
        return stop

    @transaction.atomic
    def deliver(self, user, trip_id, trip_line_id, *, proof, rating=None, comment="", latitude=None, longitude=None):
        """Paso 7: solo el conductor confirma, siempre con la foto de la remisión firmada. Sin entregas parciales."""
        trip, stop = self._open_stop(user, trip_id, trip_line_id, "entregar")
        self._require_open(stop)
        if not proof:
            raise BusinessError("La entrega se confirma con la foto de la remisión firmada.", code="missing_proof")
        s_attach = S_trip_attach()
        s_attach.attach_type("delivery_proof")  # falla antes de cambiar nada si no está configurado

        old_state = stop.state
        stop.state = "delivered"
        stop.delivery_date = timezone.now()
        stop.rating = rating
        stop.comment = comment or ""
        self.repository.save_stop(stop, user)
        R_trip_line_serie().mark(stop, "delivered")
        event = self.s_trip.events.register(trip, user, f"Entrega confirmada parada {stop.sequence}", line=stop,
                                            from_state=old_state, to_state="delivered",
                                            latitude=latitude, longitude=longitude)
        s_attach.attach_files(trip, user, [proof], "delivery_proof", line=stop, event=event,
                              latitude=latitude, longitude=longitude)
        self._after_stop_finished(trip, stop, user)
        return stop

    @transaction.atomic
    def register_return(self, user, trip_id, trip_line_id, *, reason, files=None, latitude=None, longitude=None):
        """Devolución de la parada completa; la cantidad vuelve a quedar pendiente en el pedido."""
        trip, stop = self._open_stop(user, trip_id, trip_line_id, "registrar devolución")
        self._require_open(stop)
        if not (reason or "").strip():
            raise BusinessError("Indica el motivo de la devolución.")

        old_state = stop.state
        stop.state = "returned"
        stop.is_return = True
        stop.return_reason = reason
        stop.delivery_date = timezone.now()
        self.repository.save_stop(stop, user)
        R_trip_line_serie().mark(stop, "returned", exclude_returned=False)
        event = self.s_trip.events.register(trip, user, f"Devolución parada {stop.sequence}", line=stop,
                                            from_state=old_state, to_state="returned", description=reason,
                                            latitude=latitude, longitude=longitude)
        if files:
            S_trip_attach().attach_files(trip, user, files, "return", line=stop, event=event,
                                         latitude=latitude, longitude=longitude)
        self._after_stop_finished(trip, stop, user)
        return stop
