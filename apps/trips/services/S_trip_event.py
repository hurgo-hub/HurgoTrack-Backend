from django.db import transaction

from enginedj.base.services import BaseService

from enginedj.base.exceptions import BusinessError, BusinessNotFound, BusinessPermissionError
from enginedj.base.services.permissions import has_perm
from apps.trips.entity import E_trip_event
from apps.trips.repository import R_trip, R_trip_event, R_trip_line

BUSY_STATES = ("assigned", "in_route", "delivering")


class S_trip_event(BaseService[E_trip_event]):

    def __init__(self):
        super().__init__(repository=R_trip_event(), entity_class=E_trip_event)
        self.repository: R_trip_event = self.repository

    def register(self, trip, user, name, **kwargs):
        return self.repository.register(trip, user, name, **kwargs)

    @transaction.atomic
    def report_novelty(self, user, trip_id, *, name, description="", trip_line_id=None, files=None,
                       latitude=None, longitude=None):
        """Paso 6: el conductor asignado (o despacho) reporta un imprevisto, con fotos opcionales."""
        from apps.drivers.services import S_driver
        from apps.trips.services.S_trip_attach import S_trip_attach

        trip = R_trip().get_for_update(trip_id)
        if trip is None:
            raise BusinessNotFound("El viaje no existe.")
        is_driver = S_driver().is_user(trip.driver_id_id, user)
        if not has_perm(user, "trips.report_novelty_trip") or not (is_driver or has_perm(user, "trips.view_all_trip")):
            raise BusinessPermissionError("Solo el conductor asignado o despacho pueden reportar novedades.")
        if trip.state not in BUSY_STATES:
            raise BusinessError(f"No se pueden reportar novedades: el viaje {trip.code} está "
                                f"'{trip.get_state_display()}'.", code="invalid_state")
        stop = None
        if trip_line_id:
            stop = R_trip_line().get_for_update(trip, trip_line_id)
            if stop is None:
                raise BusinessNotFound("La parada no pertenece a este viaje.")
        event = self.repository.register(trip, user, name, event_type="novelty", line=stop, description=description,
                                         latitude=latitude, longitude=longitude)
        if files:
            S_trip_attach().attach_files(trip, user, files, "novelty", line=stop, event=event,
                                         latitude=latitude, longitude=longitude)
        return event
