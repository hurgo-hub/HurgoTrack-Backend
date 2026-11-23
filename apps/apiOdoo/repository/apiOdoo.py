"""Cliente JSON-RPC de Odoo (endpoint /jsonrpc, servicios common y object).

Igual que ApiSintesisRepository en arquitecturabase: lee la configuración
de settings, guarda en caché la autenticación (uid) y expone llamadas
genéricas. No sabe nada de pedidos ni viajes.
"""

import itertools

import requests
from django.conf import settings
from django.core.cache import cache

from enginedj.base.exceptions import BusinessError


class OdooError(BusinessError):
    default_code = "odoo_error"


class ApiOdooRepository:

    UID_CACHE_KEY = "odoo_api_uid"
    _ids = itertools.count(1)

    def __init__(self, force_cache: bool = False):
        self.force_cache = force_cache

    @staticmethod
    def _config() -> dict:
        config = {
            "url": (settings.ODOO_URL or "").rstrip("/"),
            "db": settings.ODOO_DB,
            "username": settings.ODOO_USERNAME,
            "api_key": settings.ODOO_API_KEY,
        }
        missing = [key for key, value in config.items() if not value]
        if missing:
            raise OdooError(f"Falta configurar Odoo: {', '.join('ODOO_' + m.upper() for m in missing)}.")
        return config

    def _call(self, service: str, method: str, *args):
        config = self._config()
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": list(args)},
            "id": next(self._ids),
        }
        response = requests.post(f"{config['url']}/jsonrpc", json=payload, timeout=settings.ODOO_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            error = data["error"]
            message = (error.get("data") or {}).get("message") or error.get("message") or str(error)
            raise OdooError(f"Odoo respondió con error: {message}")
        return data.get("result")

    def _get_uid(self) -> int:
        """uid desde caché o autenticando con usuario + API key."""
        if not self.force_cache:
            uid = cache.get(self.UID_CACHE_KEY)
            if uid:
                return uid
        config = self._config()
        uid = self._call("common", "authenticate", config["db"], config["username"], config["api_key"], {})
        if not uid:
            raise OdooError("Odoo rechazó las credenciales (ODOO_USERNAME / ODOO_API_KEY).")
        cache.set(self.UID_CACHE_KEY, uid, timeout=3600)
        return uid

    def execute_kw(self, model: str, method: str, args: list, kwargs: dict | None = None):
        config = self._config()
        return self._call("object", "execute_kw", config["db"], self._get_uid(), config["api_key"], model, method,
                          args, kwargs or {})

    def search_read(self, model: str, domain: list, fields: list, limit: int | None = None, order: str | None = None):
        kwargs = {"fields": fields}
        if limit:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search_read", [domain], kwargs)

    def message_post(self, model: str, res_id: int, body: str):
        return self.execute_kw(model, "message_post", [[res_id]], {"body": body})
