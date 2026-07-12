#!/bin/sh
set -eu

test "${SERVICE_ROLE:-}" = "web"
exec gunicorn strange_novelty.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_WORKERS:-2}" \
  --timeout "${WEB_TIMEOUT_SECONDS:-30}" \
  --graceful-timeout "${WEB_GRACEFUL_TIMEOUT_SECONDS:-30}" \
  --error-logfile -
