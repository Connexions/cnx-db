#! /usr/bin/env bash

# Exit in case of error
set -e

echo "Remove python bytecode files"
make -f Makefile.docker clean

# Build the image and wait for the database server to come up
docker-compose build
docker-compose down -v --remove-orphans # Remove possibly previous broken stacks left hanging after an error
docker-compose up -d
docker-compose exec db wait-for-it -t 30 db:5432

# Instantiate the testing database, database user, and run tests
# If these steps do not continue then there may be an issue with the container starting up.
# Run `docker-compose logs db` to diagnose
docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS testing"
docker-compose exec db psql -U postgres -c "DROP ROLE IF EXISTS tester"
docker-compose exec db psql -U postgres -c "CREATE USER tester WITH SUPERUSER PASSWORD 'tester';"
docker-compose exec db createdb -U postgres -O tester testing
docker-compose exec db make -f Makefile.docker flake8
docker-compose exec db make -f Makefile.docker doc8
docker-compose exec db make -f Makefile.docker test
