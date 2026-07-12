# Phase 8 Implementation Record: Backup, Archive, and Restore Verification

## Status

Completed on 2026-07-11. This record is non-normative; ADR-0009 remains authoritative.

## Artifact Boundaries

Human-readable export is UTF-8 current-Scene text for reading. Structured archive is a versioned portable full-Workspace semantic package. PostgreSQL backup is the disaster-recovery database boundary described in the operator runbook. None substitutes for another.

## Human-Readable Export

The export is a restrictive-permission directory with deterministic `index.txt` and one UTF-8 text file per Scene. Filenames use zero-padded ordering plus UUID, never titles. Files contain title, lifecycle, current Revision number, and exact current-pointer content. Active and archived are included; trashed is opt-in. Output is atomic, refuses overwrite by default, rejects symlinks/unsafe paths, follows no external references, and contains no operational/authentication records.

## Structured Archive

The format is `strange-novelty-workspace`, schema 1, as a directory containing `manifest.json` and six canonical UTF-8 JSON files under `records/`: Workspace, Account UUID references, Grants, Scenes, Mutation Operations, and every Scene Revision. Ordering is deterministic and stable UUIDs, lifecycle, ordering, versions, current pointers, lineage, content representation metadata, hashes, timestamps, and provenance are retained.

The manifest records format/schema/tool/application versions, time, source Workspace identity/name, same-archive restore mode, normalization/content versions, counts, exact file inventory, byte sizes, SHA-256 hashes, aggregate inventory digest, and explicit exclusions.

Excluded are passwords/authentication material, sessions, Security Events, Scene Save Requests, generic idempotency, Jobs/Attempts, search projections, provider/deployment secrets, and encryption keys. These operational records are not required to reconstruct authoritative creative state. Search is rebuilt; unfinished Jobs present after PostgreSQL recovery are separately quarantined.

## Integrity and Validation

Validation is read-only and fail-closed: directory/no-symlink structure, exact allowlisted filenames, 16-file/10-MB-file/50-MB-total/100,000-record limits, UTF-8/JSON, schema/mode, file bytes/hashes, inventory digest, counts, prohibited keys, UUID uniqueness, Workspace identity, current pointers, Scene-scoped revision numbers, lineage, operations, actors, and Grants. Errors disclose categories only.

SHA-256 detects accidental corruption; it does not provide confidentiality or trusted authenticity. Signatures and custom cryptography are deferred.

## Restore and Authority Policy

Portable restore requires an empty Workspace/Scene/Revision target, explicit confirmation, explicit isolated/non-serving acknowledgement, and every referenced Account UUID pre-existing. It never restores passwords or creates insecure Account stubs. Workspace/domain UUIDs are preserved. Grants preserve UUID/account/role but are restored revoked; owner authority requires explicit later review.

Within one transaction restore creates Workspace, revoked Grants, controlled null-current Scenes, Mutation Operations, dependency-ordered immutable Revisions, then exact current pointers/Scene versions and semantic verification. No merge, cross-Workspace import, SQL execution, constraint disabling, or partial best-effort behavior exists.

## Recovery Reconciliation

All Django sessions in the target are deleted. Phase 6 unfinished Jobs already present are quarantined with leases invalidated. All search projections are deleted and no rebuild executes automatically. The operator later enqueues rebuilds explicitly. No worker starts and no external effect runs.

## Verification and Readiness

Restore writes a restrictive canonical JSON report containing archive digest, source/target Workspace UUID, bounded counts/actions, identity/current-pointer/lineage/version checks, session/Job/projection reconciliation counts, warning categories, time, and tool version—never titles or content.

`verify_restore_readiness` requires all semantic flags from a non-dry-run report plus an explicit `--acknowledge-operational-checks` flag, but performs no cutover. Before supplying that flag, the operator must review authority, migrations/checks, a pre-activation backup, rollback, stopped workers, reconciliation, maintenance/non-serving state, and later recent-authentication policy.

## Filesystem and Encryption

Exports use sibling temporary directories and atomic replacement, restrictive permissions, no symlink following, allowlisted relative archive names, bounded sizes/counts, cleanup on failure, and no routine absolute-path output. Existing output is refused unless explicit overwrite is selected.

Encryption is external: artifacts must be encrypted in transit/at rest with keys held separately. No keys, cloud integrations, signatures, or encryption implementation are added.

## Commands

- `export_workspace_readable`
- `export_workspace_archive`
- `validate_workspace_archive`
- `restore_workspace_archive`
- `verify_restore_readiness`

All use explicit paths/scope, bounded output, and dry-run where mutation/export planning applies. Admin remains outside restore/export.

## Database and Runbook

No model or migration was added. `docs/operations/backup-and-restore-runbook.md` documents placeholder-only `pg_dump`/`pg_restore`, isolated recovery, verification, encryption, generations, readiness, rollback, and incident boundaries. No database command was executed.

## Tests and Verification

Tests cover archive structure/hashes/validation safety, readable and structured export, exclusions, overwrite/symlink handling, pointer/history preservation, restore refusal/dry-run/authority policy, reconciliation, reports/readiness, commands, and static runbook boundaries. The complete suite reports 90 passed and 93 skipped. PostgreSQL-backed cases skipped because `TEST_DATABASE_URL` was absent; SQLite was never used. The existing virtual environment supplied Django, pytest, Ruff, and mypy, but the `uv` executable was unavailable, so dependency synchronization could not be rerun.

Verification includes an attempted locked dependency sync, Django local/test/safe-production checks, migration drift, pytest, Ruff, mypy, `git diff --check`, and security/scope scans. Only dependency synchronization was unavailable because the `uv` executable was not installed in this environment.

## Known Limitations and Deferred Work

Portable restore is bounded in-memory full-Workspace only and requires pre-existing Accounts. It does not restore Security Events/Jobs/idempotency evidence, provide signatures/encryption, detect serving traffic automatically, activate Grants, rebuild search, start workers, or cut over traffic. PostgreSQL restore execution remains operator-run and untested without a safe database.

Phase 9 adds staged cross-Workspace/Story Engine import with new identities. AI, automated backup scheduling, cloud storage, production deployment, MFA, exact retention/RPO/RTO, and external key custody remain deferred.

## ADR Alignment

This implementation preserves ADR-0009's three artifact classes, identity-preserving same-archive restore, isolated validation-first flow, fail-closed semantics, revoked authority, session invalidation, integrity manifests, reconciliation, and activation separation; ADR-0010 Job quarantine; ADR-0012 projection rebuildability; and ADR-0014 operator/runbook boundaries.
