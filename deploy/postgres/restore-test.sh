#!/bin/sh
# Prueba de restauración. La corre "deploy/backup/backup.sh restore-test" en un
# contenedor aparte, con un volumen vacío (restore_test): restaura el último
# respaldo del bucket, reproduce el WAL hasta el final y revisa que la base
# responda. No archiva nada al bucket (archive-mode=off).
set -eu
D=/var/lib/postgresql/data

if [ -n "$(ls -A "$D" 2>/dev/null)" ]; then
    echo "restore-test: $D no está vacío; el volumen de prueba debe empezar vacío." >&2
    exit 1
fi
chown postgres:postgres "$D"
chmod 700 "$D"

echo "== Restaurando el último respaldo"
gosu postgres pgbackrest --stanza=hurgotrack --archive-mode=off --log-level-console=warn restore

echo "== Reproduciendo el WAL hasta el final"
gosu postgres pg_ctl -D "$D" -l /tmp/restore-test.log -w -t 900 start \
    -o "-c listen_addresses='' -c archive_mode=off"
i=0
until [ "$(gosu postgres psql -U hurgotrack -d postgres -Atc 'select pg_is_in_recovery()')" = "f" ]; do
    i=$((i + 1))
    if [ "$i" -ge 900 ]; then
        echo "restore-test: la recuperación no terminó en 15 minutos" >&2
        tail -20 /tmp/restore-test.log >&2
        exit 1
    fi
    sleep 1
done

echo "== Revisando la base restaurada"
gosu postgres psql -U hurgotrack -d hurgotrack -At \
    -c "select 'migraciones: ' || count(*) from django_migrations" \
    -c "select 'usuarios: ' || count(*) from auth_user" \
    -c "select 'viajes: ' || count(*) from trip" \
    -c "select 'pedidos: ' || count(*) from orders"
gosu postgres pg_ctl -D "$D" -m fast stop
echo "restore-test: OK"
