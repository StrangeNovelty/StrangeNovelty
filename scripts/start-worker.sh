#!/bin/sh
set -eu

test "${SERVICE_ROLE:-}" = "worker"
: "${WORKER_ID:?WORKER_ID is required}"
exec python manage.py run_worker \
  --batch-size "${WORKER_BATCH_SIZE:-1}" \
  --idle-sleep "${WORKER_IDLE_SECONDS:-1}" \
  --worker-id "${WORKER_ID}"
