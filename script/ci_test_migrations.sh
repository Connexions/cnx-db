#!/bin/bash

set -e

git fetch origin master
first_commit=$(git log --format='%h' --reverse FETCH_HEAD.. | head -1)

# keep track of which branch we are on, so we can go back to it later
if [ -z "$CI" ]
then
    current_commit=$(git symbolic-ref --short HEAD)
else
    current_commit=$(git log --format='%h' | head -1)
fi

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
dropdb -U postgres testing
createdb -U postgres -O tester testing
cnx-db init -d testing -U tester
dbmigrator --db-connection-string='dbname=testing user=tester' init

# store the schema
pg_dump -s 'dbname=testing user=tester' >old_schema.sql

# go back to the branch HEAD
git checkout $current_commit
pip install .

# mark all the repeat, deferred migrations as not applied (to make the
# calculation of the number of migrations to rollback easier)
dbmigrator --db-connection-string='dbname=testing user=tester' list | \
    awk '/deferred\*/ {print $1}' | \
    while read timestamp; do dbmigrator --db-connection-string='dbname=testing user=tester' mark -f $timestamp; done

# check the number of migrations that are going to run
applied_before=$(dbmigrator --db-connection-string='dbname=testing user=tester' list | awk 'NF>3 {applied+=1}; END {print applied}')

# run the migrations
dbmigrator --db-connection-string='dbname=testing user=tester' migrate --run-deferred

applied_after=$(dbmigrator --db-connection-string='dbname=testing user=tester' list | awk 'NF>3 {applied+=1}; END {print applied}')
steps=$((applied_after-applied_before))

# store the schema
pg_dump -s 'dbname=testing user=tester' >migrated_schema.sql

# rollback the migrations
if [ "$steps" -gt 0 ]
then
    dbmigrator --db-connection-string='dbname=testing user=tester' rollback --steps=$steps
fi

pg_dump -s 'dbname=testing user=tester' >rolled_back_schema.sql

# reset database
dropdb -U postgres testing
createdb -U postgres -O tester testing
cnx-db init -d testing -U tester
dbmigrator --db-connection-string='dbname=testing user=tester' init

pg_dump -s 'dbname=testing user=tester' >new_schema.sql

# Put dev environment back, if not on Travis
if [ -z "$CI" ]
then
    pip install -e .
fi

# check schema
rollback=$(diff -wu old_schema.sql rolled_back_schema.sql || true)
migration=$(diff -wu new_schema.sql migrated_schema.sql || true)

if [ -n "$rollback" ]
then
    echo "Rollback test failed:"
    diff -wu old_schema.sql rolled_back_schema.sql || true
fi

if [ -n "$migration" ]
then
    echo "Migration test failed:"
    diff -wu new_schema.sql migrated_schema.sql || true
fi

if [ -z "$rollback" -a -z "$migration" ]
then
    echo "Migration and rollback tests passed."
    exit 0
fi

exit 1
