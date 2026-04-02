#!/usr/bin/env bash

set -e
set -x

ENVIRONMENT=test coverage run -m pytest tests/ --ignore=tests/integration "$@"
coverage report
coverage html --title "${@-coverage}"
