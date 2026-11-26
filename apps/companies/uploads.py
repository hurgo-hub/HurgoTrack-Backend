"""Rutas de los archivos subidos (remisiones, facturas, SOAT...).

``/media/`` solo exige sesión iniciada (Caddy pregunta a ``/api/auth/session/status/``), así que
la ruta de un archivo no puede ser adivinable: con el nombre original, un usuario de una empresa
podría bajar el documento de otra probando rutas. Cada archivo queda en
``<carpeta>/<esquema>/<año>/<mes>/<32 hex>-<nombre>``: el esquema es el de la empresa con la que se
trabaja (``c<id>``) o ``public`` (lo de Hurgo).
"""

import os
import re
import secrets

from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.text import get_valid_filename

_TOKEN = re.compile(r"^[0-9a-f]{32}-")


@deconstructible
class PrivateUpload:
    def __init__(self, folder: str):
        self.folder = folder

    def __call__(self, instance, filename):
        from django.db import connection

        schema = getattr(connection, "schema_name", None) or "public"
        name = get_valid_filename(os.path.basename(filename))[-80:] or "archivo"
        return f"{self.folder}/{schema}/{timezone.now():%Y/%m}/{secrets.token_hex(16)}-{name}"

    def __eq__(self, other):
        return isinstance(other, PrivateUpload) and other.folder == self.folder


def display_name(file) -> str:
    """Nombre para mostrar: el original, sin la carpeta ni el prefijo aleatorio."""
    base = (getattr(file, "name", "") or "").rsplit("/", 1)[-1]
    return _TOKEN.sub("", base)
