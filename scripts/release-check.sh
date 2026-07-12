#!/bin/sh
set -eu

python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py showmigrations --plan
exec python manage.py verify_production_readiness --static --allow-maintenance
