#!/bin/bash

set -e

export DB_URL='postgresql://tester:tester@localhost:5432/testing'

# set up the database
dropdb -U postgres testing
createdb -U postgres -O tester testing
cnx-db init

# store the schema
pg_dump -s 'dbname=testing user=tester' >schema.sql

# Recreate the DB, and restore it
dropdb -U postgres testing
createdb -U postgres -O tester testing
psql -U postgres testing -f schema.sql
pg_dump -s 'dbname=testing user=tester' >restored_schema.sql

# check schema
dumprestore=$(diff -wu schema.sql restored_schema.sql || true)

if [ -n "$dumprestore" ]
then
    echo "Dump/restore test failed:"
    diff -wu schema.sql restored_schema.sql || true
    exit 1
fi

exit 0
