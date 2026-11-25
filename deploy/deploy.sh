#!/bin/sh
# Despliegue desde tu PC (WSL) al VPS. El servidor no necesita acceso a GitHub.
#
#   ./deploy/deploy.sh                          # despliegues normales
#   API_DOMAIN=api.midominio.com ./deploy/deploy.sh   # el primero: crea el .env del VPS
#
# 1. Arma el core (EngineDj) desde la etiqueta de requirements.txt (vH0.1.0), no
#    desde los cambios sin commit de tu carpeta EngineDj.
# 2. Empaqueta este backend tal como está en tu carpeta (respeta .gitignore: sin
#    .env, .venv, media ni db.sqlite3).
# 3. Lo sube por SSH, conserva el .env del servidor y corre build + up.
#
# Variables opcionales: VPS, REMOTE_DIR, ENGINEDJ_DIR, SSH, SCP, PYTHON,
# API_DOMAIN y FRONTEND_ORIGIN (solo si el VPS todavía no tiene .env).
set -eu
cd "$(dirname "$0")/.."

VPS="${VPS:-deploy@169.58.28.127}"
REMOTE_DIR="${REMOTE_DIR:-HurgoTrack/backend}"  # relativo al home del usuario del VPS
ENGINEDJ_DIR="${ENGINEDJ_DIR:-../EngineDj}"
# ssh/scp de Windows: usan la llave cargada en el ssh-agent de Windows (id_contabo).
SSH="${SSH:-/mnt/c/Windows/System32/OpenSSH/ssh.exe}"
SCP="${SCP:-/mnt/c/Windows/System32/OpenSSH/scp.exe}"
PYTHON="${PYTHON:-.venv/bin/python}"

TAG="$(sed -n 's/.*EngineDj\.git@\([^ ]*\).*/\1/p' requirements.txt)"
[ -n "$TAG" ] || { echo "No encontré la etiqueta de EngineDj en requirements.txt" >&2; exit 1; }
CORE_REV="$(git -C "$ENGINEDJ_DIR" rev-parse --short "${TAG}^{commit}")"
BACKEND_REV="$(git rev-parse --short HEAD)$(git diff --quiet HEAD -- 2>/dev/null || echo '+cambios')"
echo "Core:    EngineDj $TAG ($CORE_REV)"
echo "Backend: $BACKEND_REV"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT INT TERM
mkdir -p "$WORK/src" "$WORK/pkg/vendor"

# 1. Core desde la etiqueta
git -C "$ENGINEDJ_DIR" archive "$TAG" | tar -x -C "$WORK/src"
"$PYTHON" -m pip wheel --quiet --no-deps -w "$WORK/pkg/vendor" "$WORK/src"
echo "Paquete: $(ls "$WORK/pkg/vendor")"
printf 'backend=%s\nenginedj=%s %s\nfecha=%s\n' "$BACKEND_REV" "$TAG" "$CORE_REV" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$WORK/pkg/RELEASE"

# 2. Backend: archivos versionados y nuevos que existen en la carpeta
git ls-files -co --exclude-standard | while IFS= read -r f; do
    [ -e "$f" ] && printf '%s\n' "$f"
done > "$WORK/files"
tar -czf "$WORK/release.tgz" -T "$WORK/files" -C "$WORK/pkg" vendor RELEASE
echo "Release: $(du -h "$WORK/release.tgz" | cut -f1)"

# 3. Subir, instalar y levantar
"$SCP" -q "$(wslpath -w "$WORK/release.tgz")" "$VPS:/tmp/hurgotrack-release.tgz"
"$SSH" -o ServerAliveInterval=30 "$VPS" \
    "set -e; rm -rf ~/$REMOTE_DIR.new; mkdir -p ~/$REMOTE_DIR.new; \
     tar -xzf /tmp/hurgotrack-release.tgz -C ~/$REMOTE_DIR.new; rm -f /tmp/hurgotrack-release.tgz; \
     sh ~/$REMOTE_DIR.new/deploy/remote-up.sh '$REMOTE_DIR' '${API_DOMAIN:-}' '${FRONTEND_ORIGIN:-}'"
