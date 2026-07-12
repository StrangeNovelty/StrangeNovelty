# Backup and Restore Runbook

## Prerequisites

- Stop workers and place web serving in maintenance/non-serving mode.
- Confirm the intended environment, PostgreSQL database, release, and migration state.
- Keep credentials outside commands, Git, archives, logs, and shell history. Use protected PostgreSQL password-file or platform injection facilities.
- Create a rollback point before any activation operation.

## PostgreSQL Backup

Use PostgreSQL-supported tooling appropriate to the deployment. Conceptual custom-format example:

```console
pg_dump --format=custom --file='<protected-backup-file>' '<database-name>'
```

Do not put passwords in arguments. Protect the artifact with restrictive permissions and reviewed encryption at rest/in transit. Keep multiple bounded generations and an off-host copy according to later retention policy.

## Backup Verification

Record tool/database compatibility, artifact size, creation result, and a cryptographic file hash in protected operational evidence. A successful write is not proven recovery. Periodically restore a representative generation into an isolated empty database and perform the checks below.

## Isolated PostgreSQL Restore

Create a compatible empty database through the deployment's approved operator process, then conceptually:

```console
pg_restore --dbname='<isolated-empty-database>' --clean=false '<protected-backup-file>'
```

Do not restore directly over a serving database. Validate roles, privileges, extensions, migration history, constraints, identities, current pointers, revision chains, Grants, and authentication state. Invalidate sessions, quarantine unfinished Jobs, reset search projections, and keep workers stopped.

## Application Archive Export and Validation

```console
python manage.py export_workspace_archive --workspace '<workspace-uuid>' --output '<archive-directory>'
python manage.py validate_workspace_archive --archive '<archive-directory>'
```

The portable archive is not a PostgreSQL backup. Store it encrypted using external reviewed tooling; its hashes detect corruption but provide neither confidentiality nor trusted authenticity.

## Structured Restore

Use only an isolated non-serving target with all required Account UUIDs already established safely:

```console
python manage.py restore_workspace_archive --archive '<archive-directory>' --report '<verification-report>' --dry-run
python manage.py restore_workspace_archive --archive '<archive-directory>' --report '<verification-report>' --confirm --acknowledge-isolated
```

Portable restore preserves Workspace/domain UUIDs, restores Grants revoked, invalidates sessions, quarantines unfinished Jobs already present, deletes search projections, and starts no worker.

## Readiness and Controlled Activation

```console
python manage.py verify_restore_readiness --report '<verification-report>' --acknowledge-operational-checks
python manage.py check --deploy --settings='<production-settings-module>'
```

Before traffic changes, separately confirm owner/Grant review, migration compatibility, a pre-activation backup, rollback steps, stopped workers, session invalidation, Job reconciliation, projection rebuild planning, and post-activation verification. The readiness command never starts services or switches traffic.

## Rollback and Incidents

Preserve the original backup/archive and verification evidence. On validation, migration, or cutover failure, stop, retain the isolated target for bounded investigation, and return to the last verified compatible release/database. Never repair archive content silently or expose manuscript text in incident logs.

## Retention and Encryption

Exact schedules, generations, RPO, RTO, storage locations, and expiry remain operational decisions. Backups and archives require encryption in transit and at rest with keys stored separately. Key loss and expiry must be tested. Digital signatures and custom cryptography are not implemented.
