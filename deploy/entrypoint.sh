#!/bin/sh
# Arranque de los contenedores del backend. Solo "web" (RUN_MIGRATIONS=1) migra,
# junta los estáticos y sincroniza roles y workflows; worker y beat solo arrancan.
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    python manage.py seed_workflows
fi

exec "$@"
