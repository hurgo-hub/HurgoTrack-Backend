"""Cliente de las APIs de Satrack (https://developer.satrack.com).

- Token: ``POST {SATRACK_AUTH_URL}/api/v1/Keycloak/authenticate`` (multipart) con
  ``Client_id`` + ``Grant_type`` (``password`` con ``Username``/``Password`` o
  ``client_credentials`` con ``Client_Secret``). Responde ``access_token`` y
  ``expires_in`` (segundos); se guarda en caché hasta poco antes de vencer.
- Posiciones: ``POST {SATRACK_LOCATION_URL}/location`` con ``{"query": "<GraphQL>"}``
  y ``Authorization: Bearer``. Consultas ``last(serviceCodes: [...])`` (último
  evento por placa) y ``byDate(...)`` (eventos de hasta 5 días atrás).

Igual que ApiOdooRepository: no sabe nada de viajes ni del mapa.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.core.cache import cache

from enginedj.base.exceptions import BusinessError

# Campos de evento que documenta Satrack (Localization and Events API).
EVENT_FIELDS = (
    "serviceCode latitude longitude address town state district suburb direction "
    "generationDate generationDateEpoch generationDateGMT generationDateEpochGMT recordDate recordDateEpoch "
    "unifiedEventCode description speed odometer temperature ignition deviceType vehicleStatus locationStatus "
    "batteryLevel customerPoint customerPointDistance customerPointName id samePlaceMinutes"
)
DATE_FORMAT = "%Y/%m/%d %H:%M:%S"  # formato de initialDate / endDate en byDate
PLATE_RE = re.compile(r"^[A-Z0-9]{3,10}$")


class SatrackError(BusinessError):
    default_code = "satrack_error"


class SatrackPlateError(SatrackError):
    """Satrack respondió 400: alguna placa no pertenece al usuario de la integración."""

    default_code = "satrack_plate_error"


def normalize_plate(plate) -> str:
    """``abc-123`` -> ``ABC123`` (el serviceCode de Satrack es la placa)."""
    return re.sub(r"[^A-Z0-9]", "", str(plate or "").upper())


def _literal(value: str) -> str:
    """Cadena GraphQL segura (las placas ya vienen validadas)."""
    return json.dumps(str(value))


@dataclass(frozen=True)
class SatrackCredentials:
    client_id: str
    client_secret: str = field(default="", repr=False)
    username: str = ""
    password: str = field(default="", repr=False)

    @classmethod
    def from_settings(cls) -> "SatrackCredentials":
        return cls(
            client_id=settings.SATRACK_CLIENT_ID,
            client_secret=settings.SATRACK_CLIENT_SECRET,
            username=settings.SATRACK_USERNAME,
            password=settings.SATRACK_PASSWORD,
        )

    @property
    def grant_type(self) -> str:
        return "password" if self.username else "client_credentials"

    def is_complete(self) -> bool:
        if not self.client_id:
            return False
        return bool(self.password) if self.username else bool(self.client_secret)

    def missing(self) -> list[str]:
        missing = [] if self.client_id else ["SATRACK_CLIENT_ID"]
        if self.username and not self.password:
            missing.append("SATRACK_PASSWORD")
        if not self.username and not self.client_secret:
            missing.append("SATRACK_USERNAME y SATRACK_PASSWORD (o SATRACK_CLIENT_SECRET)")
        return missing

    @property
    def key(self) -> str:
        """Identifica la cuenta sin exponer secretos (caché del token y agrupación de placas)."""
        return hashlib.sha256(f"{self.client_id}|{self.username}".encode()).hexdigest()[:20]

    def form(self) -> dict:
        form = {"Client_id": self.client_id, "Grant_type": self.grant_type}
        if self.grant_type == "password":
            form.update(Username=self.username, Password=self.password)
        else:
            form["Client_Secret"] = self.client_secret
        return form


class ApiSatrackRepository:

    def __init__(self, credentials: SatrackCredentials | None = None):
        self.credentials = credentials or SatrackCredentials.from_settings()

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------
    @staticmethod
    def _url(setting: str, path: str) -> str:
        return f"{(getattr(settings, setting) or '').rstrip('/')}{path}"

    def _post(self, url: str, **kwargs) -> requests.Response:
        try:
            return requests.post(url, timeout=settings.SATRACK_TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            raise SatrackError(f"Satrack no responde ({exc.__class__.__name__}).") from exc

    @property
    def _token_cache_key(self) -> str:
        return f"satrack_token_{self.credentials.key}"

    def token(self, force: bool = False) -> str:
        """access_token desde caché o autenticando en Keycloak."""
        if not force:
            token = cache.get(self._token_cache_key)
            if token:
                return token
        if not self.credentials.is_complete():
            raise SatrackError(f"Falta configurar Satrack: {', '.join(self.credentials.missing())}.")
        files = {name: (None, value) for name, value in self.credentials.form().items()}
        response = self._post(self._url("SATRACK_AUTH_URL", "/api/v1/Keycloak/authenticate"), files=files)
        if response.status_code in (400, 401, 403):
            raise SatrackError("Satrack rechazó las credenciales (SATRACK_CLIENT_ID / usuario / clave).")
        if response.status_code >= 400:
            raise SatrackError(f"Satrack respondió {response.status_code} al autenticar.")
        data = response.json() or {}
        token = data.get("access_token")
        if not token:
            # Con credenciales malas Satrack responde 200 con access_token null.
            raise SatrackError("Satrack rechazó las credenciales (SATRACK_CLIENT_ID / usuario / clave).")
        expires_in = int(data.get("expires_in") or 300)
        cache.set(self._token_cache_key, token, timeout=max(expires_in - 30, 30))
        return token

    def graphql(self, query: str) -> dict:
        """Ejecuta una consulta en la API de localización; reautentica una vez si el token venció."""
        url = self._url("SATRACK_LOCATION_URL", "/location")
        response = None
        for attempt in range(2):
            headers = {"Authorization": f"Bearer {self.token(force=attempt > 0)}"}
            response = self._post(url, json={"query": query}, headers=headers)
            if response.status_code != 401:
                break
            cache.delete(self._token_cache_key)
        if response.status_code == 400:
            raise SatrackPlateError("Alguna placa no pertenece al usuario de la integración en Satrack.")
        if response.status_code == 401:
            raise SatrackError("Satrack rechazó el token (inválido o vencido).")
        if response.status_code >= 400:
            raise SatrackError(f"Satrack respondió {response.status_code}.")
        body = response.json() or {}
        if body.get("errors"):
            messages = "; ".join(str(error.get("message", error)) for error in body["errors"])
            raise SatrackError(f"Satrack respondió con error: {messages}")
        return body.get("data") or {}

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @staticmethod
    def _plates(plates) -> list[str]:
        cleaned = [normalize_plate(p) for p in plates]
        invalid = [p for p in cleaned if not PLATE_RE.match(p)]
        if invalid:
            raise SatrackError(f"Placas inválidas: {', '.join(invalid)}.")
        return list(dict.fromkeys(cleaned))

    def last(self, plates) -> list[dict]:
        """Último evento de cada placa."""
        plates = self._plates(plates)
        if not plates:
            return []
        codes = ", ".join(_literal(p) for p in plates)
        data = self.graphql(f"query {{ last(serviceCodes: [{codes}]) {{ {EVENT_FIELDS} }} }}")
        return data.get("last") or []

    def by_date(self, plate, initial_date, end_date, page: int = 1, items_per_page: int = 100,
                event_codes=None) -> list[dict]:
        """Eventos de una placa entre dos fechas (``datetime`` en hora local, máximo 5 días atrás)."""
        (plate,) = self._plates([plate])
        args = [
            f"serviceCode: {_literal(plate)}",
            f"currentPage: {int(page)}",
            f"itemsPerPage: {int(items_per_page)}",
            f"initialDate: {_literal(initial_date.strftime(DATE_FORMAT))}",
            f"endDate: {_literal(end_date.strftime(DATE_FORMAT))}",
        ]
        if event_codes:
            args.append(f"eventCodes: [{', '.join(_literal(c) for c in event_codes)}]")
        data = self.graphql(
            f"query {{ byDate({', '.join(args)}) {{ pagination {{ currentPage }} events {{ {EVENT_FIELDS} }} }} }}"
        )
        return (data.get("byDate") or {}).get("events") or []
