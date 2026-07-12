# Maintenance Mode Runbook

## Enable

Set `MAINTENANCE_MODE=true` through reviewed runtime configuration and restart web and worker roles. Liveness remains healthy; web and worker readiness fail. Authenticated safe reads and login/logout remain available, while ordinary HTTP mutations receive a generic 503 maintenance page. Workers refuse to claim new Jobs. Management commands remain operator-controlled.

## During Maintenance

Stop or drain workers before migrations, restoration, high-impact repair, or incident containment. Do not infer Workspace authority from maintenance access. Monitor running leases and reconcile expired or ambiguous effects. Never use maintenance as permission for ad hoc database writes.

## Disable

Complete migration/recovery checks, session and authority review, Job/import/AI reconciliation, search reset/rebuild planning, web and worker readiness, synthetic smoke checks, and backup verification. Set the flag false, restart roles, verify readiness, and monitor bounded alerts.
