"""Posiciones e historial GPS de los vehículos de la flota desde Satrack."""

from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from enginedj.base.exceptions import BusinessNotFound

from apps.apiSatrack.repository import (
    ApiSatrackRepository,
    SatrackCredentials,
    SatrackError,
    SatrackPlateError,
    normalize_plate,
)

BATCH_SIZE = 50  # placas por consulta ``last``
HISTORY_DAYS = 5  # Satrack guarda eventos de hasta 5 días atrás
HISTORY_PAGE_SIZE = 100
HISTORY_MAX_POINTS = 5000
MISSING_PLATE_SECONDS = 600  # placa que Satrack no reconoce: no se vuelve a preguntar en 10 min
_MISSING = {"_missing": True}


def to_position(event: dict) -> dict | None:
    """Evento de Satrack -> posición para el mapa (``coordinates`` en [lng, lat] como mapcn / MapLibre)."""
    lat, lng = event.get("latitude"), event.get("longitude")
    if lat is None or lng is None:
        return None
    lat, lng = float(lat), float(lng)
    if lat == 0 and lng == 0:
        return None
    return {
        "plate": normalize_plate(event.get("serviceCode")),
        "coordinates": [lng, lat],
        "longitude": lng,
        "latitude": lat,
        "speed": event.get("speed"),
        "direction": event.get("direction"),
        "address": event.get("address"),
        "town": event.get("town"),
        "state": event.get("state"),
        "event_code": event.get("unifiedEventCode"),
        "description": event.get("description"),
        "ignition": event.get("ignition"),
        "odometer": event.get("odometer"),
        "vehicle_status": event.get("vehicleStatus"),
        "location_status": event.get("locationStatus"),
        "battery_level": event.get("batteryLevel"),
        "temperature": event.get("temperature"),
        "customer_point": event.get("customerPointName"),
        "same_place_minutes": event.get("samePlaceMinutes"),
        "generation_date": event.get("generationDate"),
        "generation_date_gmt": event.get("generationDateGMT"),
        "epoch": event.get("generationDateEpochGMT"),
        "event_id": event.get("id"),
    }


def vehicle_gps(vehicle):
    """``fleet.M_vehicle_gps`` del vehículo o None."""
    try:
        return vehicle.vehicle_gps_vehicle_id
    except Exception:  # RelatedObjectDoesNotExist
        return None


class S_satrack:

    @property
    def enabled(self) -> bool:
        return bool(settings.SATRACK_ENABLED)

    def require_enabled(self):
        if not self.enabled:
            raise SatrackError("La integración con Satrack está apagada (SATRACK_ENABLED=False).")

    def credentials_for(self, vehicle) -> SatrackCredentials | None:
        """Credenciales propias del GPS del vehículo (operador Satrack) o las globales del .env.

        None si el vehículo tiene GPS de otro operador o no hay credenciales.
        """
        default = SatrackCredentials.from_settings()
        gps = vehicle_gps(vehicle)
        if gps is not None and gps.is_active:
            if "satrack" not in (gps.operator or "").lower():
                return None
            if gps.username or gps.api_secret:
                own = SatrackCredentials(
                    client_id=gps.api_key or default.client_id,
                    client_secret=gps.api_secret,
                    username=gps.username,
                    password=gps.password,
                )
                if own.is_complete():
                    return own
        return default if default.is_complete() else None

    # ------------------------------------------------------------------
    # Vehículos de la flota
    # ------------------------------------------------------------------
    @staticmethod
    def vehicles(vehicle_ids=None, plates=None) -> list:
        """Vehículos activos (todos, o los pedidos por id / placa)."""
        from apps.fleet.models import M_vehicle

        qs = M_vehicle.objects.filter(is_active=True).select_related("vehicle_gps_vehicle_id").order_by("plate")
        if vehicle_ids or plates:
            wanted = {normalize_plate(p) for p in plates or []}
            return [v for v in qs if v.pk in set(vehicle_ids or []) or normalize_plate(v.plate) in wanted]
        return list(qs)

    def vehicle(self, vehicle_id=None, plate=None):
        found = self.vehicles([vehicle_id] if vehicle_id else None, [plate] if plate else None)
        if not found:
            raise BusinessNotFound("El vehículo no existe.")
        return found[0]

    def fleet_positions(self, vehicle_ids=None, plates=None) -> dict:
        """Última posición de los vehículos de la flota (marcadores del mapa)."""
        self.require_enabled()
        vehicles = self.vehicles(vehicle_ids, plates)
        positions, errors = self.last_positions(vehicles)
        markers = []
        for vehicle in vehicles:
            position = positions.get(vehicle.pk)
            data = {"id": f"vehicle-{vehicle.pk}", "vehicle_id": vehicle.pk, "plate": normalize_plate(vehicle.plate),
                    "found": position is not None, "satrack": self.credentials_for(vehicle) is not None}
            markers.append({**data, **position, "plate": data["plate"]} if position else data)
        return {"satrack": {"enabled": True, "errors": errors}, "vehicles": markers}

    # ------------------------------------------------------------------
    # Última posición
    # ------------------------------------------------------------------
    @staticmethod
    def _cache_key(plate: str) -> str:
        return f"satrack_pos_{plate}"

    def _fetch(self, repository: ApiSatrackRepository, plates: list[str]) -> dict[str, dict | None]:
        """Última posición por placa; si Satrack rechaza el lote, pregunta placa por placa."""
        try:
            events = repository.last(plates)
        except SatrackPlateError:
            if len(plates) == 1:
                return {plates[0]: None}
            found = {}
            for plate in plates:
                found.update(self._fetch(repository, [plate]))
            return found
        found = dict.fromkeys(plates)
        for event in events:
            position = to_position(event)
            if position and position["plate"] in found:
                found[position["plate"]] = position
        return found

    def last_positions(self, vehicles) -> tuple[dict[int, dict | None], list[str]]:
        """``({vehicle_id: posición o None}, errores)``. Un error de una cuenta no tumba las demás."""
        positions, errors = {}, []
        groups: dict[str, tuple[SatrackCredentials, dict[str, int]]] = {}
        for vehicle in vehicles:
            positions[vehicle.pk] = None
            plate = normalize_plate(vehicle.plate)
            cached = cache.get(self._cache_key(plate))
            if cached is not None:
                positions[vehicle.pk] = None if cached.get("_missing") else cached
                continue
            credentials = self.credentials_for(vehicle)
            if credentials is None:
                continue
            groups.setdefault(credentials.key, (credentials, {}))[1][plate] = vehicle.pk

        for credentials, plates in groups.values():
            repository = ApiSatrackRepository(credentials)
            plate_list = list(plates)
            for start in range(0, len(plate_list), BATCH_SIZE):
                chunk = plate_list[start:start + BATCH_SIZE]
                try:
                    found = self._fetch(repository, chunk)
                except SatrackError as exc:
                    errors.append(exc.message)
                    continue
                for plate, position in found.items():
                    if position is None:
                        cache.set(self._cache_key(plate), _MISSING, timeout=MISSING_PLATE_SECONDS)
                    else:
                        cache.set(self._cache_key(plate), position, timeout=settings.SATRACK_POSITIONS_CACHE_SECONDS)
                    positions[plates[plate]] = position
        return positions, list(dict.fromkeys(errors))

    # ------------------------------------------------------------------
    # Historial
    # ------------------------------------------------------------------
    def history(self, vehicle, start=None, end=None, event_codes=None, max_points: int = HISTORY_MAX_POINTS) -> dict:
        """Eventos del vehículo entre ``start`` y ``end`` (por defecto, las últimas 2 horas).

        Devuelve ``coordinates`` ([lng, lat] en orden) listo para ``MapRoute`` de mapcn.
        """
        self.require_enabled()
        credentials = self.credentials_for(vehicle)
        if credentials is None:
            raise SatrackError(f"El vehículo {vehicle.plate} no tiene GPS Satrack configurado.")
        now = timezone.now()
        end = min(end or now, now)
        start = start or end - timedelta(hours=2)
        floor = now - timedelta(days=HISTORY_DAYS) + timedelta(minutes=1)
        clamped = start < floor
        start = max(start, floor)
        if start >= end:
            raise SatrackError("La fecha inicial debe ser anterior a la final (y de máximo 5 días atrás).")

        repository = ApiSatrackRepository(credentials)
        local_start, local_end = timezone.localtime(start), timezone.localtime(end)
        events, truncated = [], False
        max_pages = max(1, max_points // HISTORY_PAGE_SIZE)
        for page in range(1, max_pages + 1):
            batch = repository.by_date(vehicle.plate, local_start, local_end, page=page,
                                       items_per_page=HISTORY_PAGE_SIZE, event_codes=event_codes)
            events.extend(batch)
            if len(batch) < HISTORY_PAGE_SIZE:
                break
        else:
            truncated = True

        points = [p for p in (to_position(e) for e in events) if p]
        points.sort(key=lambda p: (p["epoch"] is None, p["epoch"] or 0, p["generation_date"] or ""))
        return {
            "vehicle_id": vehicle.pk,
            "plate": normalize_plate(vehicle.plate),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "clamped": clamped,
            "truncated": truncated,
            "coordinates": [p["coordinates"] for p in points],
            "points": points,
        }
