#!/bin/bash

set -e

if [ -f /tmp/cnxarchive_dump.tar ]
then
    # To acquire a database dump see
    # https://github.com/Connexions/devops/wiki/How-To%3A-Get-a-Slim-Database-Dump

    # Increase postgresql.conf checkpoint_segment for loading data
    echo "checkpoint_segments = 10000" >>$PGDATA/postgresql.conf
    # pg_ctl commands copied from postgres:9.4 docker-entrypoint.sh
    pg_ctl -D $PGDATA -m fast -w stop
    pg_ctl -D $PGDATA -o "-c listen_addresses='localhost'" -w start

    # Re-create the existing database
    echo "DROP SCHEMA IF EXISTS public CASCADE" | psql -U $POSTGRES_USER $DB_NAME
    psql -v ON_ERROR_STOP=1 --username $POSTGRES_USER "$POSTGRES_DB" <<-EOSQL
        DROP DATABASE "${DB_NAME}";
        ALTER USER ${DB_USER} WITH SUPERUSER;
        CREATE DATABASE "${DB_NAME}" OWNER ${DB_USER};
EOSQL

    # Load data
    tar -O -xf /tmp/cnxarchive_dump.tar cnxarchive_dump_without_files.sql.gz | gunzip -c | psql -U $DB_USER $DB_NAME -f -
    tar -O -xf /tmp/cnxarchive_dump.tar cnxarchive_index_files.txt.gz | gunzip -c | psql -U $DB_USER $DB_NAME -c "ALTER TABLE files DISABLE TRIGGER USER; COPY files (fileid, md5, sha1, file, media_type) FROM STDIN; ALTER TABLE files ENABLE TRIGGER USER;"
    tar -O -xf /tmp/cnxarchive_dump.tar cnxarchive_other_files.txt.gz | gunzip -c | psql -U $DB_USER $DB_NAME -c "ALTER TABLE files DISABLE TRIGGER USER; COPY files (fileid, md5, sha1, file, media_type) FROM STDIN; ALTER TABLE files ENABLE TRIGGER USER;"
    tar -O -xf /tmp/cnxarchive_dump.tar cnxarchive_index_module_files.txt.gz | gunzip -c | psql -U $DB_USER $DB_NAME -c "ALTER TABLE module_files DISABLE TRIGGER USER; COPY module_files (module_ident, fileid, filename) FROM STDIN; ALTER TABLE module_files ENABLE TRIGGER USER;"

    # Remove superuser privileges from DB_USER
    psql -v ON_ERROR_STOP=1 --username $POSTGRES_USER "$POSTGRES_DB" <<-EOSQL
        ALTER USER ${DB_USER} WITH NOSUPERUSER;
EOSQL

    # Reset virtualenv python code
    psql -U $DB_USER $DB_NAME -c 'DROP SCHEMA IF EXISTS venv CASCADE'
    # Reset checkpoint_segment after loading data
    sed -i 's/checkpoint_segments = 10000/checkpoint_segments = 10/' $PGDATA/postgresql.conf
fi
