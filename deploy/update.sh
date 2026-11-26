#!/bin/sh
# Actualiza el backend en el VPS desde GitHub y reinicia los servicios.
#
#   ~/HurgoTrack/backend/deploy/update.sh               # rama main
#   BRANCH=sergio ~/HurgoTrack/backend/deploy/update.sh
#
# - Backend: git pull de hurgo-hub/HurgoTrack-Backend (esta carpeta es un clon).
# - Core: arma EngineDj desde la etiqueta de requirements.txt (vH0.1.1) con la
#   copia de ~/HurgoTrack/enginedj (repo privado; se baja con una deploy key de
#   solo lectura). Si esa copia no está, usa el paquete que ya hay en vendor/.
# - docker compose build + up. Las migraciones y seed_workflows corren al
#   arrancar "web". El .env y el .env.backup de esta carpeta no los toca git.
set -eu
cd "$(dirname "$0")/.."
BRANCH="${BRANCH:-main}"
ENGINEDJ_DIR="${ENGINEDJ_DIR:-$HOME/HurgoTrack/enginedj}"

[ -f .env ] || { echo "Falta .env: corre ./deploy/init-env.sh <dominio>" >&2; exit 1; }

# 1. Backend
git fetch --quiet origin "$BRANCH"
git checkout --quiet "$BRANCH"
git merge --ff-only --quiet "origin/$BRANCH"
BACKEND_REV="$(git rev-parse --short HEAD)"

# 2. Core desde la etiqueta
TAG="$(sed -n 's/.*EngineDj\.git@\([^ ]*\).*/\1/p' requirements.txt)"
if [ -d "$ENGINEDJ_DIR/.git" ]; then
    git -C "$ENGINEDJ_DIR" fetch --quiet --force --tags origin
    CORE_REV="$(git -C "$ENGINEDJ_DIR" rev-parse --short "${TAG}^{commit}")"
    W="$(mktemp -d)"
    trap 'rm -rf "$W"' EXIT INT TERM
    mkdir -p "$W/src" "$W/out"
    git -C "$ENGINEDJ_DIR" archive "$TAG" | tar -x -C "$W/src"
    # El paquete se arma en un contenedor: el servidor no necesita pip.
    # SOURCE_DATE_EPOCH (fecha del commit) hace que la misma etiqueta dé siempre
    # el mismo .whl, así Docker reutiliza la capa de dependencias si no cambió.
    EPOCH="$(git -C "$ENGINEDJ_DIR" log -1 --format=%ct "${TAG}^{commit}")"
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e SOURCE_DATE_EPOCH="$EPOCH" \
        -v "$W/src:/src" -v "$W/out:/out" python:3.14-slim \
        pip wheel --quiet --disable-pip-version-check --no-deps -w /out /src
    mkdir -p vendor
    find vendor -name 'enginedj-*.whl' -delete
    cp "$W"/out/enginedj-*.whl vendor/
else
    CORE_REV="paquete ya existente"
    ls vendor/enginedj-*.whl >/dev/null 2>&1 || {
        echo "No hay core: falta $ENGINEDJ_DIR (deploy key de EngineDj) y no hay paquete en vendor/" >&2
        exit 1
    }
    echo "Aviso: no está $ENGINEDJ_DIR; uso el core que ya está en vendor/" >&2
fi

printf 'backend=%s (%s)\nenginedj=%s %s\nfecha=%s\n' "$BACKEND_REV" "$BRANCH" "$TAG" "$CORE_REV" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > RELEASE
echo "== $(tr '\n' ' ' < RELEASE)"

# 3. Construir y levantar
docker compose build --pull
docker compose up -d --remove-orphans
docker compose ps
