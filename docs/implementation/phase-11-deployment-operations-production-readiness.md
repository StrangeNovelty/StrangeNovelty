# Phase 11 Implementation Record: Deployment, Operations, and Production Readiness

## Status

Completed on 2026-07-11 as a deployable foundation, not private-content production approval. ADR-0014 remains authoritative. ADR-0005's MFA gate is still unmet and blocks launch with real private manuscript content.

## Selected Topology and Image

Version 1 uses one vendor-neutral Docker-compatible OCI image on a Linux container host. Platform infrastructure supplies TLS termination/reverse proxying, external secret injection, managed or separately operated PostgreSQL, immutable image storage, process restart, and encrypted external backup storage. There is no Kubernetes, Redis, broker, daemon supervisor, or cloud-vendor configuration.

`Dockerfile` is a multi-stage build using version-pinned Python 3.14.6 slim Bookworm and uv 0.11.28 images. It performs frozen production dependency synchronization, compiles `psycopg-c` with build-only PostgreSQL headers, collects WhiteNoise hashed static assets, copies no Git/private/test/database/archive material, and runs as UID/GID 10001. The runtime source is read-only-capable; only platform temporary locations need be writable. The base images are version-pinned but not digest-pinned; deployment must record the resolved base and final image digests.

## Process Roles

The same image exposes separate exec-form scripts:

- `start-web.sh`: Gunicorn WSGI with bounded configurable workers/timeouts and graceful shutdown;
- `start-worker.sh`: existing PostgreSQL Job worker with required unique worker identity and bounded batch/idle controls;
- `release-migrate.sh`: one serialized deploy check, migration plan, and explicit migration execution;
- `release-check.sh`: non-mutating deploy, migration-drift/plan, and static-readiness checks.

Web and worker startup never execute migrations. Worker claiming fails closed during maintenance. Migration credentials are not available to routine roles.

## Configuration, Secrets, and Database Roles

Production settings require explicit signing secret, PostgreSQL URL with credentials, hosts, HTTPS CSRF origins, trusted-proxy acknowledgement, service role, release/build/source/configuration identity, and bounded values. DEBUG, wildcard hosts, fake AI, missing TLS proxy trust, unsafe logging levels, and malformed release identity fail closed. Cookies and redirect are secure, PostgreSQL requires TLS, connection health checks/timeouts are bounded, email delivery is disabled, requests are size-limited, and optional AI availability is not readiness-critical.

Signing, database, future provider, backup, encryption-key, break-glass, and deployment credentials remain externally injected and purpose-separated. Encryption keys remain separate from ciphertext/backups. `postgresql-role-boundaries.md` defines migration, web, worker, backup, restore, and inspection roles; routine roles are never owners or superusers.

## Health, Maintenance, and Release Identity

`/health/live/` is process-local and never queries PostgreSQL. `/health/ready/` performs a bounded connection and migration-state check, requires web role, and returns generic `ready`/`not-ready` only. `check_worker_readiness` supplies the worker probe. Optional providers are never contacted.

Maintenance is environment-controlled. Liveness stays available; readiness fails; authenticated safe reads and login/logout remain available; all other HTTP mutations return a generic accessible 503 page; workers refuse new claims; management commands remain operator-controlled.

Every production release requires bounded release version, source commit, build identifier, and `config-v1` configuration schema. Runtime containers never invoke Git.

## Logging, Metrics, and Alerts

Production uses console JSON through `PrivacySafeJsonFormatter`, emitting timestamp, severity, bounded event classification, service role, release, and optional validated correlation ID. It deliberately discards raw log messages and exceptions from formatted output. Local logging remains Django's usable default.

`operational_snapshot` defines an internal vendor-neutral metric boundary for Job state, import state, AI Request state, and search backlog. Labels are fixed vocabularies only; UUIDs, Workspace/Account/Scene IDs, titles, content, queries, filenames, IPs, agents, and errors are prohibited. Collection/export remains deployment-specific.

The production checklist defines alert classes for web/worker/readiness, generic errors, PostgreSQL, migration, backup/restore, Job backlog/leases/failures/quarantine, authentication anomalies, configuration/secrets, storage, search backlog, import quarantine, and AI quarantine. Thresholds and channels remain deployment-specific.

## Static Files and Supply Chain

Gunicorn 23 and WhiteNoise 6 are isolated in the locked production group with `psycopg-c`; runtime and build versions are resolved in `uv.lock`. WhiteNoise uses compressed manifest storage and collects during image build. Static files contain no manuscript data. Dependencies, base/final image digests, scan evidence, license review, changes, and release notes are reviewed each release. Scanning does not prove vulnerability absence.

## Release, Rollback, and Recovery

The deployment runbook requires maintenance, worker pause, verified backup, static checks, migration-plan review, one migration task, web readiness/smoke checks, worker readiness, and controlled return. Expand-and-contract is required where releases overlap. Destructive/long migrations require lock/capacity/backup/restore review.

Rollback retains the previous compatible image digest and rolls web/worker together only after schema and Job compatibility review. Database rollback/restoration is separate. Phase 8 recovery requires isolated restore validation, session invalidation, unfinished Job/import/AI quarantine, search reset, authority review, and controlled activation.

## Runbooks and Readiness Command

Added deployment, incident response, secret rotation, maintenance, break-glass, PostgreSQL-role, and production-readiness documents; the existing backup/restore runbook remains controlling for recovery.

`verify_production_readiness` prints only bounded check/outcome classifications. Static mode avoids database connectivity and checks configuration, release identity, PostgreSQL backend, secure transport, static storage, Job registry, maintenance, fake AI exclusion, and runbook presence. Normal mode adds PostgreSQL/migration readiness. `--private-content` adds the fail-closed MFA gate and currently exits nonzero. It never claims deployment occurred.

## Verification

The complete suite reports 116 passed and 110 PostgreSQL-dependent skips. Local/test/production Django checks passed. `check --deploy` completed with only the intentionally conservative HSTS subdomain/preload warnings; those controls remain disabled until all production subdomains and preload permanence are reviewed. Migration drift, Ruff, formatting, mypy, and `git diff --check` passed.

uv successfully updated `uv.lock` with Gunicorn 23.0.0 and WhiteNoise 6.12.0. Local all-group synchronization reached the existing `psycopg-c` build and failed because host PostgreSQL development headers are absent; the OCI build explicitly installs `libpq-dev` in its build stage. The default development environment was restored, and the two locked pure-Python production packages were installed locally for production-settings verification.

Static production readiness passed. Database-required readiness failed generically because no safe PostgreSQL database was configured. Private-content readiness failed specifically at the MFA gate as designed. No Docker/Podman executable was available, so no image build occurred; Dockerfile, scripts, ignore rules, dependencies, and tests were validated statically.

## Remaining Blockers and Limitations

WebAuthn, bounded TOTP fallback, recovery/session assurance, and `MFA_ENFORCED` remain the primary production blocker. Hosting platform, registry, final image/base digests, secret manager, DNS/TLS, PostgreSQL roles/grants, backup schedule/storage, telemetry collector, alert thresholds/channels, resource limits, vulnerability scanner, signing/SBOM, and operational exercise evidence remain deployment-specific work. Production launch is not approved.

## ADR Alignment

This phase implements ADR-0014's environment, immutable release, role, configuration, secret, health, logging, metric, migration, rollback, access, incident, and recovery boundaries; preserves ADR-0005's MFA requirement; uses ADR-0010 worker/reconciliation semantics; and integrates ADR-0009 verified restoration without provisioning or deploying infrastructure.
