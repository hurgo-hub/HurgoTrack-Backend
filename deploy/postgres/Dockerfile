# PostgreSQL 17 de Hurgo Track: imagen oficial (Debian) + pgBackRest para los
# respaldos con archivo continuo de WAL. Trae también pgaudit (fase de auditoría);
# no se activa hasta agregarlo a shared_preload_libraries.
FROM postgres:17-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends pgbackrest postgresql-17-pgaudit \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/pgbackrest /var/lib/pgbackrest /var/spool/pgbackrest /tmp/pgbackrest \
    && chown -R postgres:postgres /var/log/pgbackrest /var/lib/pgbackrest /var/spool/pgbackrest /tmp/pgbackrest

COPY pgbackrest.conf /etc/pgbackrest/pgbackrest.conf
COPY archive-push.sh /usr/local/bin/archive-push
COPY restore-test.sh /usr/local/bin/restore-test
RUN chmod 755 /usr/local/bin/archive-push /usr/local/bin/restore-test \
    && chmod 644 /etc/pgbackrest/pgbackrest.conf
