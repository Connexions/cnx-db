#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username postgres <<-EOSQL
    CREATE USER ${DB_USER};
    CREATE USER backups;
    ALTER DATABASE "${DB_NAME}" OWNER TO ${DB_USER};
    GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO ${POSTGRES_USER};
    GRANT ALL PRIVILEGES ON DATABASE "${DB_NAME}" TO ${DB_USER};
    \c "${DB_NAME}" ${POSTGRES_USER}
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA PUBLIC TO ${POSTGRES_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA PUBLIC TO ${DB_USER};
EOSQL

if [ -z "`ls /docker-entrypoint-initdb.d/*.sql.gz`" -a -z  "`ls /docker-entrypoint-initdb.d/*.sql`" ]; then
    cnx-db init
fi

# ??? Is this really what we want to be doing?
psql -v ON_ERROR_STOP=1 --username postgres "$DB_NAME" <<-EOSQL
    REASSIGN OWNED BY ${POSTGRES_USER} TO ${DB_USER};
EOSQL
