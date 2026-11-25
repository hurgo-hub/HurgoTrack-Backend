"""Producción: Docker Compose en el VPS (ver ``docker-compose.yml`` y ``deploy/``).

Las variables vienen del ``.env`` del VPS (lo crea ``deploy/init-env.sh``) vía ``env_file``.
"""

from .base import *  # noqa: F401,F403

DEBUG = False

# Caddy termina el HTTPS y le pasa la petición a daphne por http.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"

SIMPLE_JWT = {
    **SIMPLE_JWT,
    "AUTH_COOKIE_SECURE": True,
    "AUTH_COOKIE_SAMESITE": "None",
}

# Redis compartido por todos los procesos (daphne, worker y beat): caché de los
# workflows y de Satrack, WebSockets y broker de Celery.
REDIS_URL = env("REDIS_URL", default="redis://redis:6379").rstrip("/")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "KEY_PREFIX": env("CACHE_PREFIX", default="hurgotrack"),
    },
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [f"{REDIS_URL}/2"]},
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"{REDIS_URL}/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_ALWAYS_EAGER = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
