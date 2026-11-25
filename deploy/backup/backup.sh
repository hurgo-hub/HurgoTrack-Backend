#!/bin/sh
# Respaldos de Hurgo Track en el VPS (los programa install-cron.sh).
#
#   backup.sh init           # una vez: crea el repositorio en el bucket (pgBackRest y restic)
#   backup.sh full           # respaldo completo de PostgreSQL (domingos)
#   backup.sh diff           # diferencial de PostgreSQL (lunes a sábado)
#   backup.sh media          # archivos subidos (restic) y limpieza según retención
#   backup.sh check          # revisa los dos repositorios
#   backup.sh restore-test   # restaura el último respaldo en un contenedor aparte (mensual)
#   backup.sh info           # muestra los respaldos guardados
#
# El WAL se archiva solo, cada minuto como máximo (archive_command de "db").
# Cada resultado queda en ~/HurgoTrack/backup-status (última ejecución correcta).
set -eu
cd "$(dirname "$0")/../.."

STATUS="$HOME/HurgoTrack/backup-status"
ACTION="${1:-}"

conf() { sed -n "s/^$1=//p" .env.backup 2>/dev/null | tail -1; }
[ -n "$(conf PGBACKREST_REPO1_S3_BUCKET)" ] && [ -n "$(conf PGBACKREST_REPO1_CIPHER_PASS)" ] || {
    echo "Falta configurar el bucket: ./deploy/backup/configure-backup.sh" >&2
    exit 1
}

pg() { docker compose exec -T -u postgres db pgbackrest --stanza=hurgotrack "$@"; }
rs() { docker compose --profile backup run --rm -T restic "$@"; }

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] backup.sh $ACTION"
case "$ACTION" in
    init)
        pg stanza-create
        pg check
        rs cat config >/dev/null 2>&1 || rs init
        ;;
    full | diff)
        pg --type="$ACTION" backup
        ;;
    media)
        rs backup /data/media --tag media
        # La retención (35 días + 1 por mes) debe ser más larga que el Object
        # Lock del bucket, o prune no puede borrar lo vencido.
        rs forget --tag media --keep-within 35d --keep-monthly 12 --prune
        ;;
    check)
        pg check
        rs check
        ;;
    restore-test)
        docker compose --profile backup run --rm -T restore-test
        docker volume rm hurgotrack_restore_test >/dev/null
        ;;
    info)
        pg info
        rs snapshots --tag media
        exit 0
        ;;
    *)
        sed -n '2,12p' "$0"
        exit 2
        ;;
esac

mkdir -p "$(dirname "$STATUS")"
touch "$STATUS"
grep -v "^$ACTION " "$STATUS" > "$STATUS.tmp" || true
echo "$ACTION $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$STATUS.tmp"
mv "$STATUS.tmp" "$STATUS"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $ACTION OK"
