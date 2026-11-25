"""Settings de hurgotrack."""

from pathlib import Path

import environ
from celery.schedules import crontab

from enginedj.settings import *  # noqa: F401,F403

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
# La sesión va en cookies (access_token / refresh_token): el frontend usa credentials: "include".
CORS_ALLOW_CREDENTIALS = True

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"

# Apps de Hurgo Track, una por grupo del modelo de datos. El core (tabla ``base``, empresas,
# usuarios y utilidades compartidas) vive en EngineDj, rama HurgoCore (app ``enginedj.base``).
INSTALLED_APPS += [
    "apps.locations",
    "apps.fleet",
    "apps.drivers",
    "apps.orders",
    "apps.trips",
    "apps.apiOdoo",
    "apps.stock",
    "apps.apiSatrack",
]

# Integración con Odoo (app apps.apiOdoo). Apagada por defecto: con
# ODOO_ENABLED=False la confirmación de pedidos no consulta Odoo.
ODOO_ENABLED = env.bool("ODOO_ENABLED", default=False)
ODOO_URL = env("ODOO_URL", default="")
ODOO_DB = env("ODOO_DB", default="")
ODOO_USERNAME = env("ODOO_USERNAME", default="")
ODOO_API_KEY = env("ODOO_API_KEY", default="")
ODOO_TIMEOUT = env.int("ODOO_TIMEOUT", default=20)
# Estados de purchase.order que permiten confirmar el pedido en Hurgo Track.
ODOO_CONFIRMED_PURCHASE_STATES = env.list("ODOO_CONFIRMED_PURCHASE_STATES", default=["purchase", "done"])

# Integración con Satrack (app apps.apiSatrack): posiciones GPS para el mapa.
# Doc: https://developer.satrack.com. Token por Keycloak (externalsecurityapi) y
# posiciones por GraphQL (locationintegrationapi). Con SATRACK_ENABLED=False el
# mapa sigue funcionando con origen y paradas, sin vehículos.
# Credenciales: SATRACK_CLIENT_ID + (SATRACK_USERNAME y SATRACK_PASSWORD) o
# SATRACK_CLIENT_SECRET. Un vehículo con GPS propio (fleet.M_vehicle_gps, operador
# "Satrack") usa sus credenciales: username/password y api_key = client id,
# api_secret = client secret.
SATRACK_ENABLED = env.bool("SATRACK_ENABLED", default=False)
SATRACK_AUTH_URL = env("SATRACK_AUTH_URL", default="https://externalsecurityapi.satrack.com")
SATRACK_LOCATION_URL = env("SATRACK_LOCATION_URL", default="https://locationintegrationapi.satrack.com/api")
SATRACK_CLIENT_ID = env("SATRACK_CLIENT_ID", default="")
SATRACK_CLIENT_SECRET = env("SATRACK_CLIENT_SECRET", default="")
SATRACK_USERNAME = env("SATRACK_USERNAME", default="")
SATRACK_PASSWORD = env("SATRACK_PASSWORD", default="")
SATRACK_TIMEOUT = env.int("SATRACK_TIMEOUT", default=20)
# Segundos que se reutiliza la última posición de un vehículo (el frontend puede
# refrescar el mapa seguido sin pegarle a Satrack en cada petición).
SATRACK_POSITIONS_CACHE_SECONDS = env.int("SATRACK_POSITIONS_CACHE_SECONDS", default=30)

# Clave Fernet para cifrar credenciales (GPS). Generar con:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

DATABASES = {
    "default": env.db(),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
if "postgresql" in DATABASES["default"]["ENGINE"]:
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = env.int(
        "DB_CONNECT_TIMEOUT", default=5
    )

# Celery. En desarrollo se usa memoria para no depender de Redis/AMQP.
# Para un worker real: CELERY_BROKER_URL=redis://localhost:6379/0 y
# CELERY_RESULT_BACKEND=django-db (resultados en PostgreSQL vía django_celery_results).
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="memory://")
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="cache+memory://",
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_RESULT_EXTENDED = True
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=30 * 60)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=25 * 60)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Las tareas periódicas se editan desde el admin (django_celery_beat).
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    **CELERY_BEAT_SCHEDULE,
    "fleet-check-document-expirations": {
        "task": "fleet.tasks.check_document_expirations",
        "schedule": crontab(hour=6, minute=0),
    },
}
# Días de anticipación para avisar vencimiento de SOAT / revisión técnico-mecánica / licencia.
HURGO_EXPIRATION_WARNING_DAYS = env.int("HURGO_EXPIRATION_WARNING_DAYS", default=30)

ROOT_URLCONF = "config.urls"

# REST_FRAMEWORK viene de enginedj.settings: autenticación solo por la cookie "access_token"
# (CookieJWTAuthentication). Web y app móvil inician sesión con POST /api/auth/token/.

# WSGI_APPLICATION y ASGI_APPLICATION vienen de enginedj.settings:
#   enginedj.wsgi.application
#   enginedj.asgi.application

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

ENGINEDJ = {
    **ENGINEDJ,
    "CACHE_PREFIX": "hurgotrack",
}
