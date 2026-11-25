#!/bin/sh
# Configura el bucket de respaldos en el VPS. Interactivo: tú escribes los datos
# del bucket (la llave secreta no se ve en pantalla) y el script genera las
# claves de cifrado de pgBackRest y restic. Escribe .env.backup (permisos 600),
# que solo leen los contenedores db, restic y restore-test.
#
#   ./deploy/backup/configure-backup.sh
#
# Si .env.backup ya existe, conserva las claves de cifrado (si cambian, los
# respaldos que ya están en el bucket quedan ilegibles).
#
# IMPORTANTE: guarda PGBACKREST_REPO1_CIPHER_PASS y RESTIC_PASSWORD fuera del
# VPS (gestor de contraseñas). Si se pierde el servidor, sin ellas los respaldos
# no se pueden leer.
set -eu
cd "$(dirname "$0")/../.."
F=.env.backup

old() { [ -f "$F" ] && sed -n "s/^$1=//p" "$F" | tail -1 || true; }
gen() { openssl rand -base64 48 | tr -d '\n=+/' | cut -c1-64; }
ask() {  # ask VAR "Pregunta" [valor actual]
    printf '%s [%s]: ' "$2" "${3:-}" >&2
    read -r v
    [ -n "$v" ] || v="${3:-}"
    printf '%s' "$v"
}

echo "Datos del bucket S3 compatible (Backblaze B2 o Cloudflare R2)."
echo "B2: endpoint s3.<región>.backblazeb2.com, región p. ej. us-west-004."
ENDPOINT="$(ask E "Endpoint (sin https://)" "$(old PGBACKREST_REPO1_S3_ENDPOINT)")"
REGION="$(ask R "Región" "$(old PGBACKREST_REPO1_S3_REGION)")"
BUCKET="$(ask B "Bucket" "$(old PGBACKREST_REPO1_S3_BUCKET)")"
KEY_ID="$(ask K "Key ID (keyID / Access Key ID)" "$(old PGBACKREST_REPO1_S3_KEY)")"
printf 'Application key / Secret (no se ve; Enter = dejar la actual): ' >&2
stty -echo 2>/dev/null || true
read -r SECRET
stty echo 2>/dev/null || true
echo >&2
[ -n "$SECRET" ] || SECRET="$(old PGBACKREST_REPO1_S3_KEY_SECRET)"
for v in ENDPOINT REGION BUCKET KEY_ID SECRET; do
    eval "[ -n \"\$$v\" ]" || { echo "Falta $v" >&2; exit 1; }
done

PG_PASS="$(old PGBACKREST_REPO1_CIPHER_PASS)"; [ -n "$PG_PASS" ] || PG_PASS="$(gen)"
RESTIC_PASS="$(old RESTIC_PASSWORD)"; [ -n "$RESTIC_PASS" ] || RESTIC_PASS="$(gen)"

umask 077
cat > "$F.tmp" <<EOF
# Respaldos de Hurgo Track (deploy/backup/configure-backup.sh, $(date -u +%Y-%m-%d)).
# Guarda las dos claves de cifrado fuera del VPS.

# pgBackRest (PostgreSQL + WAL)
PGBACKREST_REPO1_S3_ENDPOINT=$ENDPOINT
PGBACKREST_REPO1_S3_REGION=$REGION
PGBACKREST_REPO1_S3_BUCKET=$BUCKET
PGBACKREST_REPO1_S3_URI_STYLE=host
PGBACKREST_REPO1_S3_KEY=$KEY_ID
PGBACKREST_REPO1_S3_KEY_SECRET=$SECRET
PGBACKREST_REPO1_CIPHER_PASS=$PG_PASS

# restic (archivos subidos), mismo bucket en la carpeta restic/
RESTIC_REPOSITORY=s3:https://$ENDPOINT/$BUCKET/restic
RESTIC_PASSWORD=$RESTIC_PASS
AWS_ACCESS_KEY_ID=$KEY_ID
AWS_SECRET_ACCESS_KEY=$SECRET
AWS_DEFAULT_REGION=$REGION
EOF
mv "$F.tmp" "$F"
chmod 600 "$F"
echo "Listo: $(pwd)/$F (permisos 600)."
echo "Sigue: docker compose up -d db  y luego  ./deploy/backup/backup.sh init"
