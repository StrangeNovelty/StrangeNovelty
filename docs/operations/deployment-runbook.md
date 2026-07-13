# Deployment Runbook

## Preconditions

- Private-content launch remains blocked until WebAuthn and bounded TOTP fallback are implemented and verified.
- Use an isolated production PostgreSQL database, external secret injection, platform TLS termination, encrypted external backup storage, and one immutable OCI image identified by digest.
- Confirm the latest PostgreSQL backup and representative isolated restore verification before destructive or long-running migration work.
- Keep the previous schema-compatible image available by immutable digest.

## Build

Build the checked-out release without secret build arguments. Inject `RELEASE_VERSION`, `SOURCE_COMMIT`, `BUILD_IDENTIFIER`, and `CONFIGURATION_SCHEMA_VERSION=config-v1` at runtime. Tag with a bounded release identifier, never a floating `latest` tag. The image uses one codebase and supports web, worker, migration, checks, and management commands.

The build must use `uv.lock`, collect static files with hashed manifest storage, exclude `.env`, Git metadata, private data, tests, databases, exports, and backups, and run as UID/GID 10001. Record image digest, source commit, dependency-lock digest, and scan result. Scanning is evidence, not proof of absence of vulnerabilities.

## Configuration and Secrets

Inject production-only values through the hosting platform's reviewed secret/configuration mechanism. Required configuration includes Django secret, PostgreSQL URL, explicit hosts/origins, trusted-proxy acknowledgement, service role, release identity, maintenance flag, and bounded process limits. Never place values in image layers, command arguments, repository files, logs, or browser configuration.

TLS terminates at the platform reverse proxy, which must overwrite the forwarded-proto header. Application-to-PostgreSQL transport requires TLS. Do not expose the application directly without the trusted proxy boundary.

## Release Order

1. Enable maintenance and stop worker claiming.
2. Verify backup completion, integrity, external encryption, and restore-test recency.
3. Run the image's `release-check.sh`; its static validation explicitly permits the active maintenance window but does not declare serving readiness.
4. Review `showmigrations --plan`, schema compatibility, locks, expected duration, and rollback constraints.
5. Run `release-migrate.sh` once with the migration role and credential.
6. Start the web role with `start-web.sh`; migrations are never run by web startup.
7. Check `/health/live/` and `/health/ready/` using bounded platform probes.
8. Start the worker role with `start-worker.sh`, verify `check_worker_readiness`, and execute
   a one-shot empty-queue check in a controlled environment.
9. Disable maintenance only after migration, web, and worker checks pass. Confirm web
   readiness and worker readiness again.
10. For staging, run the authenticated checks under
   `docs/operations/staging-synthetic-account-runbook.md`: password-manager autofill,
   primary WebAuthn, Workspace, existing synthetic Scene, Search, AI request shell without
   provider invocation, private cache headers, logout, and post-logout denial. Record only
   bounded pass/fail evidence and never credential or fixture content.
11. Monitor bounded alerts and logs.

## Process Roles

- Web: Gunicorn WSGI, bounded worker count/timeouts, graceful termination, HTTP only.
- Worker: Django `run_worker`, bounded batch/idle/lease behavior, no HTTP.
- Migration: serialized one-off Django checks and migrations with schema authority.
- Backup/restore/inspection: separate operator identities and commands, never routine runtime credentials.

## Rollback

Pause workers and re-enable maintenance. Confirm the previous image supports the current schema and Job formats. Roll web and worker together by immutable digest. Do not reverse irreversible migrations casually or run older code against an incompatible schema. Reconcile leases, ambiguous external effects, AI Requests, imports, and search projections. Database restoration is a separate isolated recovery procedure under the backup runbook, not application rollback.

## Post-Release

Record release identity, migration result, checks, backup status, readiness, smoke-test classifications, rollback availability, and observed alerts without private content. Retain authenticated smoke-test audit evidence for 12 months under the staging synthetic-account runbook. Review dependency/license changes and release notes.
