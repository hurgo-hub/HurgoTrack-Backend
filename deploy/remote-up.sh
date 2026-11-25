#!/bin/sh
# Parte del despliegue que corre en el VPS (la llama deploy/deploy.sh).
#
#   sh remote-up.sh <dir relativo al home> [dominio] [origen del frontend]
#
# El release nuevo ya está extraído en <dir>.new. Conserva el .env del servidor,
# deja el release anterior en <dir>.prev (para volver atrás) y corre build + up.
set -eu
cd "$HOME"

DIR="${1:?Falta el directorio}"
DOMAIN="${2:-}"
FRONTEND="${3:-}"
NEW="$DIR.new"

# Configuración del respaldo (bucket y claves de cifrado), si ya existe.
if [ -f "$DIR/.env.backup" ]; then
    cp -p "$DIR/.env.backup" "$NEW/.env.backup"
fi

if [ -f "$DIR/.env" ]; then
    cp -p "$DIR/.env" "$NEW/.env"
elif [ -n "$DOMAIN" ]; then
    (cd "$NEW" && sh deploy/init-env.sh "$DOMAIN" "$FRONTEND")
else
    echo "El VPS no tiene .env todavía. Corre: API_DOMAIN=api.midominio.com ./deploy/deploy.sh" >&2
    rm -rf "$NEW"
    exit 1
fi

rm -rf "$DIR.prev"
[ -d "$DIR" ] && mv "$DIR" "$DIR.prev"
mv "$NEW" "$DIR"

cd "$DIR"
echo "== $(tr '\n' ' ' < RELEASE)"
docker compose build --pull
docker compose up -d --remove-orphans
docker compose ps
