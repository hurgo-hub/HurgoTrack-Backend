#!/bin/sh
# archive_command de PostgreSQL: sube cada segmento de WAL al bucket (cifrado).
# Sin bucket configurado no archiva nada, igual que antes de tener respaldos,
# para que pg_wal no crezca sin control.
if [ -z "${PGBACKREST_REPO1_S3_BUCKET:-}" ]; then
    exit 0
fi
exec pgbackrest --stanza=hurgotrack archive-push "$1"
