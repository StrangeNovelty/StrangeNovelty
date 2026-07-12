#!/bin/sh
set -eu

test "${SERVICE_ROLE:-}" = "migration"
python manage.py check --deploy
python manage.py showmigrations --plan
exec python manage.py migrate --noinput
