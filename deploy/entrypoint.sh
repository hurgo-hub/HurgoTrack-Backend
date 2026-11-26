#!/bin/sh
# Arranque de los contenedores del backend. Solo "web" (RUN_MIGRATIONS=1) migra,
# junta los estáticos y sincroniza roles y workflows; worker y beat solo arrancan.
# Cada empresa tiene su esquema de PostgreSQL (c<id>): primero se migra el central
# (public) y luego el de cada empresa. Los esquemas nuevos se crean al dar de alta la empresa.
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate_schemas --shared --noinput
    python manage.py migrate_schemas --tenant --noinput
    python manage.py collectstatic --noinput
    python manage.py seed_workflows
fi

exec "$@"
