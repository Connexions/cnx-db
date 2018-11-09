#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username ${POSTGRES_USER} <<-EOSQL
    CREATE USER rhaptos_admin SUPERUSER;
EOSQL

psql -v ON_ERROR_STOP=1 --username rhaptos_admin -d postgres <<-EOSQL
    CREATE USER ${DB_USER};
    CREATE USER backups;
    ALTER DATABASE "${POSTGRES_DB}" OWNER TO ${DB_USER};
    GRANT ALL PRIVILEGES ON DATABASE "${POSTGRES_DB}" TO ${DB_USER};
    \c "${POSTGRES_DB}" rhaptos_admin
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA PUBLIC TO ${DB_USER};
EOSQL


if [ -z "`ls /docker-entrypoint-initdb.d/*.sql.gz`" -a -z  "`ls /docker-entrypoint-initdb.d/*.sql`" ]; then
    cnx-db init
fi

# ??? Is this really what we want to be doing?
psql -v ON_ERROR_STOP=1 --username ${POSTGRES_USER} "$POSTGRES_DB" <<-EOSQL
    REASSIGN OWNED BY rhaptos_admin TO ${DB_USER};
EOSQL
