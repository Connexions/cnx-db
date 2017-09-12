#!/bin/bash

set -e

git fetch origin master
first_commit=$(git log --format='%h' --reverse FETCH_HEAD.. | head -1)

# keep track of which commit we are at, so we can go back to it later
current_commit=$(git log --format='%h' | head -1)

if [ -z "$first_commit" ]
then
    echo Nothing to check.
    exit
fi

# checkout the branch point
git checkout $first_commit^
pip install .

# install db-migrator and cnx-db
pip install 'db-migrator>=1.0.0'

# set up the database
sudo -u postgres dropdb testing
sudo -u postgres createdb -O tester testing
cnx-db init -d testing -U tester
dbmigrator --db-connection-string='dbname=testing user=tester' init

# store the schema
pg_dump -s 'dbname=testing user=tester' >old_schema.sql

# go back to the branch HEAD
git checkout $current_commit
pip install .

# check the number of migrations that are going to run
steps=$(dbmigrator --db-connection-string='dbname=testing user=tester' list | grep False | wc -l)

# run the migrations
dbmigrator --db-connection-string='dbname=testing user=tester' migrate --run-deferred

# store the schema
pg_dump -s 'dbname=testing user=tester' >migrated_schema.sql

# rollback the migrations
if [ "$steps" -gt 0 ]
then
    dbmigrator --db-connection-string='dbname=testing user=tester' rollback --steps=$steps
fi

pg_dump -s 'dbname=testing user=tester' >rolled_back_schema.sql

# reset database
sudo -u postgres dropdb testing
sudo -u postgres createdb -O tester testing
cnx-db init -d testing -U tester
dbmigrator --db-connection-string='dbname=testing user=tester' init

pg_dump -s 'dbname=testing user=tester' >new_schema.sql

# check schema
rollback=$(diff -u old_schema.sql rolled_back_schema.sql || true)
migration=$(diff -u new_schema.sql migrated_schema.sql || true)

if [ -n "$rollback" ]
then
    echo "Rollback test failed:"
    diff -u old_schema.sql rolled_back_schema.sql || true
fi

if [ -n "$migration" ]
then
    echo "Migration test failed:"
    diff -u new_schema.sql migrated_schema.sql || true
fi

if [ -z "$rollback" -a -z "$migration" ]
then
    echo "Migration and rollback tests passed."
    exit 0
fi

exit 1
