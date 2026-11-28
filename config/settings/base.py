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

# Un esquema de PostgreSQL por empresa (django-tenants), por aislamiento y seguridad:
# - Esquema central ("public", Hurgo): motor, usuarios, roles, empresas, flota, viajes...
# - Esquema de cada empresa ("c<id>"): sus catálogos, productos, pedidos, compras y stock.
# El core (tabla ``base``, empresas, usuarios) vive en EngineDj, rama HurgoCore.
HURGO_APPS = [
    "apps.locations",
    "apps.fleet",
    "apps.drivers",
    "apps.trips",
    "apps.companies",
    "apps.catalogs",
    "apps.apiSatrack",
]
# Apps con datos de cada empresa: sus tablas solo existen en el esquema de cada empresa
# (catálogos, productos, direcciones, pedidos, documentos, compras de Odoo y stock).
COMPANY_APPS = [
    "apps.orders",
    "apps.apiOdoo",
    "apps.stock",
]
SHARED_APPS = ["django_tenants", *INSTALLED_APPS, *HURGO_APPS]
TENANT_APPS = [*COMPANY_APPS]
INSTALLED_APPS = SHARED_APPS + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "companies.M_tenant"
TENANT_DOMAIN_MODEL = "companies.M_domain"
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

# Integración con Odoo (app apps.apiOdoo). Apagada por defecto: con
# ODOO_ENABLED=False la confirmación de pedidos no consulta Odoo.
# ODOO_SIMULATED=True: Odoo simulado para probar sin el real (compras con "Simular compra en Odoo";
# ver apps/apiOdoo/repository/simulated.py). Enciende la integración. Nunca junto a un Odoo real.
ODOO_SIMULATED = env.bool("ODOO_SIMULATED", default=False)
ODOO_ENABLED = env.bool("ODOO_ENABLED", default=False) or ODOO_SIMULATED
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
# Solo PostgreSQL: cada empresa tiene su esquema (SQLite no tiene esquemas).
if "postgresql" not in DATABASES["default"]["ENGINE"]:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("Hurgo Track requiere PostgreSQL (un esquema por empresa): revisa DATABASE_URL.")
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = env.int("DB_CONNECT_TIMEOUT", default=5)

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

# Empresa Hurgo: transportador dueño de la flota (esquema central, sin esquema propio).
# ``seed_workflows`` la crea si no existe o actualiza su nombre (se busca por NIT).
HURGO_COMPANY_NAME = env("HURGO_COMPANY_NAME", default="")
HURGO_COMPANY_NIT = env("HURGO_COMPANY_NIT", default="")
HURGO_COMPANY_DV = env("HURGO_COMPANY_DV", default="")

ROOT_URLCONF = "config.urls"

# REST_FRAMEWORK viene de enginedj.settings. Autenticación: la web por la cookie "access_token"
# (CookieJWTAuthentication, login en /api/auth/token/); la app del conductor con el encabezado
# "Authorization: Bearer" (login en /api/mobile/auth/token/). Límites de intentos por cliente.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_AUTHENTICATION_CLASSES": [
        *REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"],  # noqa: F405
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),  # noqa: F405
        "auth_identify": env("AUTH_IDENTIFY_RATE", default="20/min"),
        "mobile_login": env("MOBILE_LOGIN_RATE", default="10/min"),
    },
}

# App del conductor: sesión de 30 días y notificaciones push por Expo (Expo entrega por Firebase;
# las credenciales de Firebase se suben a EAS, no van aquí). PUSH_ENABLED=False no envía nada.
MOBILE_REFRESH_DAYS = env.int("MOBILE_REFRESH_DAYS", default=30)
PUSH_ENABLED = env.bool("PUSH_ENABLED", default=False)
EXPO_PUSH_URL = env("EXPO_PUSH_URL", default="https://exp.host/--/api/v2/push/send")
EXPO_ACCESS_TOKEN = env("EXPO_ACCESS_TOKEN", default="")

# WSGI_APPLICATION y ASGI_APPLICATION vienen de enginedj.settings:
#   enginedj.wsgi.application
#   enginedj.asgi.application

STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "media"

ENGINEDJ = {
    **ENGINEDJ,
    "CACHE_PREFIX": "hurgotrack",
}
