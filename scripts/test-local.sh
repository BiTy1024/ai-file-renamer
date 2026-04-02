#! /usr/bin/env bash

# Exit in case of error
set -e

# Use a separate project name so test containers and volumes
# are completely isolated from the dev environment.
export COMPOSE_PROJECT_NAME=ai-namer-test

docker compose down -v --remove-orphans # Clean slate for tests

if [ $(uname -s) = "Linux" ]; then
    echo "Remove __pycache__ files"
    sudo find . -type d -name __pycache__ -exec rm -r {} \+
fi

docker compose build
docker compose up -d
docker compose exec -T backend bash scripts/tests-start.sh "$@"
docker compose down -v --remove-orphans # Clean up after tests
