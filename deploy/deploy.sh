#!/bin/sh
# Despliegue desde tu PC (WSL): le pide al VPS que se actualice desde GitHub.
# Lo que se despliega es lo que está subido (push) a la rama, no tu carpeta local.
#
#   ./deploy/deploy.sh                # rama main
#   BRANCH=sergio ./deploy/deploy.sh
#
# Usa el ssh.exe de Windows con la llave cargada en el ssh-agent (id_contabo).
set -eu
cd "$(dirname "$0")/.."

VPS="${VPS:-deploy@169.58.28.127}"
BRANCH="${BRANCH:-main}"
SSH="${SSH:-/mnt/c/Windows/System32/OpenSSH/ssh.exe}"

if ! git diff --quiet HEAD -- 2>/dev/null || [ -n "$(git ls-files -o --exclude-standard)" ]; then
    echo "Aviso: tienes cambios sin commit; no se despliegan." >&2
fi
if [ "$(git rev-parse HEAD)" != "$(git rev-parse "origin/$BRANCH" 2>/dev/null || true)" ]; then
    echo "Aviso: tu HEAD no coincide con origin/$BRANCH (¿falta push o pull?). Se despliega origin/$BRANCH." >&2
fi

cd /mnt/c
exec "$SSH" -o ServerAliveInterval=30 "$VPS" "BRANCH='$BRANCH' ~/HurgoTrack/backend/deploy/update.sh"
