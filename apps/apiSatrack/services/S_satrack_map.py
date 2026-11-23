"""Datos del mapa (mapcn) para los viajes: arcos, paradas, vehículos y recorrido.

Todas las coordenadas van en ``[lng, lat]``, el orden que esperan ``MapArc``
(``from`` / ``to``) y ``MapRoute`` (``coordinates``) de mapcn. Los marcadores
traen además ``longitude`` y ``latitude`` sueltos para ``MapMarker``.
"""

from django.db.models import Prefetch
from django.utils import timezone

from apps.apiSatrack.repository import SatrackError, normalize_plate
from apps.apiSatrack.services.S_satrack import S_satrack
from apps.trips.models import M_trip_line
from apps.trips.repository.R_trip import BUSY_STATES
from apps.trips.services import S_trip
from enginedj.base.services.permissions import require_perm

ROUTE_STATES = ("in_route", "delivering", "closed")  # viajes que ya salieron: tienen recorrido
MAX_TRIPS = 200


def _point(address) -> list[float] | None:
    if address is None or address.latitude is None or address.longitude is None:
        return None
    return [float(address.longitude), float(address.latitude)]


def _marker(point, **data) -> dict:
    return {**data, "longitude": point[0], "latitude": point[1], "coordinates": point}


class S_satrack_map:

    def __init__(self):
        self.trips = S_trip()
        self.satrack = S_satrack()

    # ------------------------------------------------------------------
    # Capas de un viaje
    # ------------------------------------------------------------------
    @staticmethod
    def _trip_summary(trip) -> dict:
        driver = trip.driver_id
        driver_user = getattr(driver, "user_id", None) if driver else None
        return {
            "id": trip.pk,
            "code": trip.code,
            "state": trip.state,
            "state_label": trip.get_state_display(),
            "company": trip.company_id.name if trip.company_id_id else None,
            "plate": trip.vehicle_id.plate if trip.vehicle_id_id else None,
            "driver": (driver_user.get_full_name() or driver_user.username) if driver_user else None,
            "planned_departure": trip.planned_departure.isoformat() if trip.planned_departure else None,
            "departure_date": trip.departure_date.isoformat() if trip.departure_date else None,
        }

    def _trip_layers(self, trip, arc_mode: str = "legs") -> dict:
        """Origen, paradas y arcos. ``legs``: origen -> parada 1 -> parada 2...; ``hub``: origen -> cada parada."""
        layers = {"origins": [], "stops": [], "arcs": [], "missing_coordinates": []}
        origin = trip.origin_address_id
        origin_point = _point(origin)
        if origin_point:
            layers["origins"].append(_marker(origin_point, id=f"origin-{trip.pk}", trip_id=trip.pk,
                                             trip_code=trip.code, kind="origin", name=origin.name,
                                             address=origin.address))
        else:
            layers["missing_coordinates"].append({"trip_id": trip.pk, "kind": "origin", "address_id": origin.pk,
                                                  "name": origin.name})

        lines = sorted((line for line in trip.trip_line_trip_id.all() if line.is_active), key=lambda l: l.sequence)
        previous_point, previous_name = origin_point, origin.name
        for line in lines:
            address = line.address_id
            point = _point(address)
            if point is None:
                layers["missing_coordinates"].append({"trip_id": trip.pk, "kind": "stop", "trip_line_id": line.pk,
                                                      "address_id": address.pk, "name": address.name})
                continue
            recipient = line.recipient_id.name if line.recipient_id_id else None
            layers["stops"].append(_marker(point, id=f"stop-{line.pk}", trip_id=trip.pk, trip_code=trip.code,
                                           trip_line_id=line.pk, kind="stop", sequence=line.sequence,
                                           name=address.name, address=address.address, recipient=recipient,
                                           state=line.state, state_label=line.get_state_display()))
            source, source_name = (origin_point, origin.name) if arc_mode == "hub" else (previous_point, previous_name)
            if source:
                layers["arcs"].append({
                    "id": f"{trip.code}-{line.sequence}",
                    "trip_id": trip.pk,
                    "trip_code": trip.code,
                    "trip_line_id": line.pk,
                    "sequence": line.sequence,
                    "from": source,
                    "to": point,
                    "origin": source_name,
                    "destination": f"{recipient} · {address.name}" if recipient else address.name,
                    "state": line.state,
                    "trip_state": trip.state,
                })
            previous_point, previous_name = point, address.name
        return layers

    @staticmethod
    def _vehicle_marker(trip, position) -> dict:
        vehicle = trip.vehicle_id
        data = {"id": f"vehicle-{vehicle.pk}", "vehicle_id": vehicle.pk, "plate": normalize_plate(vehicle.plate),
                "trip_id": trip.pk, "trip_code": trip.code, "found": position is not None}
        return {**data, **position, "plate": data["plate"]} if position else data

    # ------------------------------------------------------------------
    # Mapa general: viajes activos
    # ------------------------------------------------------------------
    def overview(self, user, arc_mode: str = "legs", trip_ids=None) -> dict:
        """Viajes asignados / en camino / en reparto que el usuario puede ver, con su vehículo en Satrack."""
        require_perm(user, "trips.view_m_trip", "No tienes permiso para ver viajes.")
        qs = self.trips.repository.visible(self.trips.scope(user)).filter(state__in=BUSY_STATES)
        if trip_ids:
            qs = qs.filter(pk__in=trip_ids)
        trips = list(
            qs.select_related("company_id", "vehicle_id__vehicle_gps_vehicle_id", "driver_id__user_id",
                              "origin_address_id")
            .prefetch_related(Prefetch("trip_line_trip_id",
                                       queryset=M_trip_line.objects.select_related("recipient_id", "address_id")))
            .order_by("planned_departure", "id")[:MAX_TRIPS]
        )
        vehicles = {trip.vehicle_id_id: trip.vehicle_id for trip in trips if trip.vehicle_id_id}
        positions, errors = {}, []
        if self.satrack.enabled and vehicles:
            positions, errors = self.satrack.last_positions(vehicles.values())

        result = {"satrack": {"enabled": self.satrack.enabled, "errors": errors},
                  "trips": [], "origins": [], "stops": [], "arcs": [], "vehicles": [], "missing_coordinates": []}
        for trip in trips:
            result["trips"].append(self._trip_summary(trip))
            for key, items in self._trip_layers(trip, arc_mode).items():
                result[key].extend(items)
            if trip.vehicle_id_id:
                result["vehicles"].append(self._vehicle_marker(trip, positions.get(trip.vehicle_id_id)))
        return result

    # ------------------------------------------------------------------
    # Mapa de un viaje
    # ------------------------------------------------------------------
    def trip_map(self, user, trip_id: int, arc_mode: str = "legs", with_route: bool = True) -> dict:
        """Un viaje: arcos y paradas, posición actual del vehículo y recorrido desde la salida."""
        trip = self.trips.detail(user, trip_id)
        result = {"satrack": {"enabled": self.satrack.enabled, "errors": []}, "trip": self._trip_summary(trip),
                  **self._trip_layers(trip, arc_mode), "vehicle": None, "route": None}
        if not (self.satrack.enabled and trip.vehicle_id_id):
            return result

        vehicle = trip.vehicle_id
        positions, errors = self.satrack.last_positions([vehicle])
        result["satrack"]["errors"].extend(errors)
        result["vehicle"] = self._vehicle_marker(trip, positions.get(vehicle.pk))

        if with_route and trip.departure_date and trip.state in ROUTE_STATES:
            end = trip.closed_date if trip.state == "closed" and trip.closed_date else timezone.now()
            try:
                history = self.satrack.history(vehicle, start=trip.departure_date, end=end)
            except SatrackError as exc:
                result["satrack"]["errors"].append(exc.message)
            else:
                result["route"] = {key: history[key] for key in ("start", "end", "clamped", "truncated",
                                                                  "coordinates", "points")}
        return result
