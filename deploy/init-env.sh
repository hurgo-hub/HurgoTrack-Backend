#!/bin/sh
# Crea el .env de producción en el VPS con claves nuevas (se corre una sola vez).
#
#   ./deploy/init-env.sh api.midominio.com [https://app.midominio.com]
#
# El segundo argumento es el origen del frontend web (CORS), si ya existe.
set -eu
cd "$(dirname "$0")/.."

if [ -e .env ]; then
    echo ".env ya existe y no lo sobrescribo: tiene la clave de la base y la de cifrado." >&2
    exit 1
fi

DOMAIN="${1:?Uso: ./deploy/init-env.sh api.midominio.com [https://app.midominio.com]}"
FRONTEND="${2:-}"
IP="$(hostname -I | awk '{print $1}')"
PG_PASS="$(openssl rand -hex 24)"
SECRET_KEY="$(openssl rand -hex 50)"
FERNET_KEY="$(openssl rand -base64 32 | tr '+/' '-_')"

umask 077
cat > .env <<EOF
# Producción de Hurgo Track (deploy/init-env.sh, $(date -u +%Y-%m-%d)).
# Guarda copia segura de FIELD_ENCRYPTION_KEY y POSTGRES_PASSWORD: sin la clave
# de cifrado no se pueden leer las credenciales GPS guardadas en la base.

API_DOMAIN=$DOMAIN
DJANGO_SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=$DOMAIN,$IP,localhost
CSRF_TRUSTED_ORIGINS=https://$DOMAIN${FRONTEND:+,$FRONTEND}
CORS_ALLOWED_ORIGINS=$FRONTEND

POSTGRES_DB=hurgotrack
POSTGRES_USER=hurgotrack
POSTGRES_PASSWORD=$PG_PASS
DATABASE_URL=postgres://hurgotrack:$PG_PASS@db:5432/hurgotrack
DB_CONN_MAX_AGE=60

REDIS_URL=redis://redis:6379
CACHE_PREFIX=hurgotrack
FIELD_ENCRYPTION_KEY=$FERNET_KEY

# Empresa Hurgo (transportador, dueña de la flota). seed_workflows la crea al arrancar.
HURGO_COMPANY_NAME=
HURGO_COMPANY_NIT=
HURGO_COMPANY_DV=

# Satrack (mapa / GPS)
SATRACK_ENABLED=False
SATRACK_CLIENT_ID=
SATRACK_CLIENT_SECRET=
SATRACK_USERNAME=
SATRACK_PASSWORD=

# Odoo
ODOO_ENABLED=False
ODOO_URL=
ODOO_DB=
ODOO_USERNAME=
ODOO_API_KEY=
EOF

echo "Listo: .env creado para $DOMAIN (permisos 600)."
