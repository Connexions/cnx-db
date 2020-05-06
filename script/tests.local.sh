#! /usr/bin/env bash

# Exit in case of error
set -e

if [ $(uname -s) = "Linux" ]; then
    echo "Remove __pycache__ files"
    sudo find . -type d -name __pycache__ -exec rm -r {} \+
fi

docker-compose build
docker-compose down -v --remove-orphans # Remove possibly previous broken stacks left hanging after an error
docker-compose up -d
docker-compose exec db wait-for-it -t 10 db:5432

docker-compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS testing"
docker-compose exec db psql -U postgres -c "CREATE USER tester WITH SUPERUSER PASSWORD 'tester';"
docker-compose exec db createdb -U postgres -O tester testing
docker-compose exec db make test 
