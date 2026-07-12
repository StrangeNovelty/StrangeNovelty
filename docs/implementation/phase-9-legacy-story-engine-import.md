# Phase 9 Implementation Record: Legacy Story Engine Import

## Status

Completed on 2026-07-11. ADR-0013 remains authoritative.

## Supported Source and Safety Boundary

Phase 9 accepts only the UTF-8 JSON `story-engine-scene-export` schema 1 documented in `docs/reference/legacy-story-engine-import-format-v1.md`. It is a narrow envelope for Scene-like records and complete snapshots, not a legacy database reader. The operator supplies one regular file explicitly. The parser rejects symlinks, invalid UTF-8/JSON, unsupported versions, unsafe identifiers, duplicate identities, NULs, malformed current references, excessive files/records/text, and unknown Revision fields. It follows no path or URL and performs no executable deserialization.

The source remains outside PostgreSQL and Git. A batch stores only the source SHA-256 fingerprint, byte size, schema/system classification, and transformation version. No path or filename is stored in import rows, Jobs, findings, logs, or Security Events.

## Batch and State Machine

`ImportBatch` has UUIDv4 identity; protected Workspace/requester/approver/validation-Job references; source classification, schema, fingerprint, size, transformation and staging-integrity fingerprints; constrained state; bounded counts/failure classification; and lifecycle timestamps. States are created, validating, staged, validation-failed, awaiting-approval, approved, applying, applied, failed-terminal, cancelled, and quarantined. Services permit the implemented path validating → awaiting-approval → approved → applying → applied, with pre-apply cancellation and restore quarantine. Batch identity never grants authority.

## Staging, Findings, and Mapping

`StagedScene` stores bounded source identity, newly generated proposed Scene UUID, normalized title, mapped lifecycle/order, explicit current source Revision, fingerprint, and status. `StagedRevision` stores newly generated Revision UUID, deterministic target number, private non-authoritative normalized text, source/target hashes, optional timestamp, chronology classification, and current marker. PostgreSQL/platform storage protection is used; no custom encryption is introduced.

`ImportFinding` contains only bounded entity/source references, issue code, severity, and field category. `IdentityMapping` immutably scopes a legacy source identity to a new UUID within one Batch. `ImportProvenance` protects the applied mapping-to-Mutation-Operation relationship. Legacy IDs never become target PKs/FKs.

## Classification and Transformation

Supported source concepts are Scene identity/title, explicit active/archived/trashed lifecycle, optional ordering, explicit current snapshot, complete snapshot content, positive source sequence, and optional timezone-aware timestamp. Scene-level unknown fields become unsupported findings. Attachments, relationships, external references, settings, authentication, providers, deployment, scripts, paths, and executable formats remain unsupported or prohibited.

Text uses the existing NFC/LF normalization without trimming manuscript whitespace. Source and normalized hashes are separate. Exact transformations create bounded findings. Missing timestamps classify chronology as uncertain without inventing chronology.

## Revision Reconstruction

Every trustworthy complete source snapshot becomes one newly identified immutable Scene Revision. Target revision numbers are allocated from deterministic source-sequence order starting at one; source sequence remains provenance only. The explicit source current marker sets the target pointer, even when it is not chronologically last. The Scene version equals the number of reconstructed accepted Revisions.

The import-specific atomic creator deliberately does not fabricate the ordinary initial empty Revision. It constructs a controlled nullable-current Scene, the exact approved chain, then the current pointer/version before commit. Ordinary Scene creation behavior is unchanged.

## Mapping, Duplicates, and Conflicts

Titles are required and bounded. Lifecycle mapping is exact and unknown values fail. Ordering uses the supplied non-negative value or deterministic sparse steps of 1024; collisions advance by 1024 and warn. Exact existing-title matches warn only. Matching title, content, timestamp, or source values never merge, authorize overwrite, or establish identity. A non-empty target Workspace requires explicit acknowledgement, and only new Scene UUIDs are created.

## Authorization and Approval

Create/stage, approve, apply, cancel, and discard resolve the current active owner Grant server-side. Revocation takes effect immediately; staff/superuser flags are irrelevant. Approval separately records the Account, time, source/transformation identity, and staging fingerprint. Application reauthorizes and recomputes staging/content integrity. Changed staging invalidates approval. Source ownership claims are ignored.

## Jobs and Idempotency

Staging is performed synchronously after safe parsing, then a commit-coupled `validate_legacy_import` Job is enqueued through Phase 6 generic idempotency. Its row contains Workspace, Batch UUID, transformation version, and bounded execution fields only—never source path or content. Identical source fingerprint/Workspace/transformation staging converges on the existing Batch. The handler revalidates staged integrity and is a safe no-op when no longer actionable. Authoritative apply remains synchronous and atomic; no resumability or blind retry is claimed.

## Application and Provenance

One transaction locks and revalidates Batch, approval, Workspace authority, a freshly reread source artifact fingerprint/size, staging integrity, target UUID availability, and non-empty acknowledgement. The apply command therefore requires the same protected source path again but never persists or prints it. It creates only new Scenes, imported Mutation Operations, complete immutable Revisions, explicit lineage/current pointers/versions, applied mappings, Import Provenance, and commit-coupled search rebuild Jobs. Batch becomes applied in the same transaction. Failure rolls everything back; retry after committed success returns the prior Batch after current authorization and artifact validation.

Scene import and each imported Revision have separate bounded Mutation Operations and protected Import Provenance. Security Events remain security evidence and are not parser/domain provenance.

## Cancellation, Retention, and Recovery

Pre-apply imports may be cancelled. Applying/applied imports cannot be cancelled; transaction interruption is not post-commit rollback. Post-apply reversal remains a separate future protected design. Pre-apply staging/findings/mappings can be explicitly discarded; exact retention periods and scheduled cleanup remain deferred. Applied authoritative records and protected provenance are not deleted by staging cleanup.

`quarantine_unfinished_imports` moves created, validating, staged, awaiting-approval, approved, and applying Batches to quarantined, clears approval, and preserves applied history. Phase 8 restore invokes it alongside Job quarantine, session invalidation, and search reset. Source paths are not assumed after restore and nothing resumes automatically.

## Commands and Administration

Commands are `create_legacy_import_batch`, `validate_legacy_import`, `approve_legacy_import`, `apply_legacy_import`, `report_legacy_import`, `discard_legacy_import_staging`, and `quarantine_unfinished_imports`. Mutating approval/apply/discard actions require explicit confirmation. Output contains Batch IDs, states, and bounded counts only.

Import administration is read-only. Staged text is excluded from broad displays; paths do not exist in the schema. There are no admin approval/apply shortcuts, browser upload, or external logging integration.

## Migrations and Verification

Migrations add `legacy_imports.0001_initial`, extend Scene Revision/Mutation Operation import choices, and extend the Job allowlist/target consistency constraints. No data migration or sample import is included. PostgreSQL migrations and integration tests run only with explicit `TEST_DATABASE_URL`; SQLite is never used.

Verification covers parser safety, deterministic staging, UUID mapping, approval integrity, reconstruction, provenance, transactional search dispatch, idempotency, duplicate warnings, non-empty acknowledgement, and restore quarantine. The complete suite reports 102 passed and 100 skipped; PostgreSQL-backed import cases skipped because `TEST_DATABASE_URL` was absent, and SQLite was never used. Django local/test/safe-production checks, migration drift, Ruff, mypy, `git diff --check`, and scope/security scans passed. Locked dependency synchronization was attempted but the `uv` executable was unavailable in this environment; the existing project virtual environment supplied all verification tools.

## Known Limitations and Deferred Work

The format covers only Scene-like records and trustworthy complete snapshots. No extractor, direct database reader, attachment/relationship import, merge UI, browser upload, checkpointed apply, automated reversal, scheduled cleanup, or cross-Workspace import exists. Exact retention and transaction-size production limits remain later operational decisions. Phase 10 adds AI Suggestions without changing import authority.

## ADR Alignment

This implementation follows ADR-0013's staged one-way transformation, new identities, explicit approval, conservative reconstruction, bounded all-or-nothing apply, and restore quarantine; ADR-0010's PostgreSQL Job/idempotency semantics; ADR-0009's distinction between import and identity-preserving restoration; and ADR-0008's explicit UUID, constraint, and migration boundaries.
