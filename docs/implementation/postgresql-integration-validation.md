# PostgreSQL Runtime Integration Validation

## Status and safety boundary

Completed on 2026-07-11 against an isolated, user-owned PostgreSQL 16 cluster inside the current WSL Ubuntu environment. No system-managed cluster was started or changed. No production, remote, shared, or development-authoritative database was contacted. All Accounts, Workspace data, Scene records, import material, AI records, credentials, and MFA evidence were synthetic and disposable.

## Local environment

Ubuntu 24.04 already supplied PostgreSQL 16.14 server/client packages and `build-essential`. The stopped system cluster on the default port was classified unrelated and left untouched. A fresh cluster was initialized under `$HOME/.local/share/strange-novelty-postgres`, with its socket in a restrictive sibling directory and PostgreSQL bound only to `127.0.0.1` on high port 55439. A one-day self-signed local certificate enabled the production settings' required TLS boundary. The directory was absent before initialization.

The bounded `strange_novelty_test_runner` role had LOGIN and CREATEDB only: no superuser, role creation, replication, or bypass-RLS authority. CREATEDB was required for Django's temporary `test_strange_novelty_test` database. Runtime-generated credentials existed only in mode-0600 `/tmp` files, were never printed or committed, and were deleted during cleanup.

PostgreSQL server and client version: 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1).

## Dependencies

`uv lock --check` and `uv sync --locked` passed with the binary Psycopg test implementation. Locked all-groups/production synchronization was attempted. `psycopg-c` 3.3.4 could not build because `libpq-dev`/`pg_config.h` was absent. Installation of only `libpq-dev` was authorized and attempted, but local `sudo` required interactive authentication that was not supplied; the attempt was cancelled without package changes. The lockfile and dependency versions remain unchanged. The controlled production image still must provide libpq development headers.

## Migration-from-zero and physical schema

The complete migration chain applied successfully from an empty `strange_novelty_test` database across Django and every project app. `showmigrations --plan` showed the chain applied, and `makemigrations --check --dry-run` reported no drift. Local, test, safe production, and deploy checks used PostgreSQL only; no SQLite backend was introduced.

Bounded catalog inspection found:

- UUID primary keys on all project-owned Account, Workspace, Scene/history, security, Job/idempotency, search projection, import/provenance, AI, MFA, challenge, recovery, assurance, and throttle records;
- only Django-generated Account many-to-many join tables used bigint surrogate keys, not project-owned domain identities;
- 105 project check constraints;
- the `scene_search_vector_gin` PostgreSQL GIN index;
- 71 protective project foreign keys and zero project cascading foreign keys;
- physical tables for Scene Save Requests, Security Events, Jobs/Attempts/Idempotency, legacy import provenance, AI Requests/Suggestions/provider effects, and MFA/session assurance;
- no Phase 8 archive model and no parallel domain integer identity.

The Account migration remained first in the project chain before dependent application records. Migration execution and the integration suite exercised Workspace/Grant consistency, Scene/Revision/Mutation Operation constraints, immutable history, save idempotency, Job states/leases, search publication, import mappings, AI provenance, and MFA secret/session boundaries.

## Complete PostgreSQL test result

Final run:

- 234 passed;
- 0 failed;
- 0 skipped;
- 110 PostgreSQL-backed tests executed that had previously been skipped;
- pytest duration 79.59 seconds.

Coverage executed owner bootstrap, normalized-email authentication, Workspace authorization and Grant revocation, WebAuthn boundaries, encrypted TOTP, one-time recovery codes, assurance/session revocation and database throttling; Scene creation, immutable complete Revisions, dual concurrency and idempotent editor saves; Job rollback/idempotency/SKIP LOCKED/competing claims/leases/retries/quarantine; PostgreSQL SearchVectors, GIN-backed queries, stale-worker protection and lifecycle filtering; archive export/validation/restore; staged import/reconstruction/provenance; deterministic fake AI Suggestions, stale-source protection and application; and restore quarantine for Jobs, imports, AI, sessions, challenges, recovery state, and search projections.

## Defects found and corrected

PostgreSQL execution exposed genuine issues hidden by the earlier database-free run:

1. `select_for_update()` attempted to lock nullable `current_revision` outer joins. Scene, save-idempotency, search-indexing, and AI request services now use `of=("self",)` so only the authoritative Scene row is locked.
2. An unsaved `Account()` reports Django authentication semantics as true. The Scene authorization service now rejects model instances still in the adding state as unauthenticated.
3. The login template omitted generic non-field authentication errors. It now renders the bounded generic message and accurately describes password as the first factor.
4. PostgreSQL tests were corrected where they called `bytes.casefold()`, searched the archive manifest's explicit exclusion declaration as though it were stored projection data, or revoked Grants without the required `revoked_at` timestamp. Assertions and fixture updates now respect the accepted constraints without weakening them.

Focused regressions and the complete suite passed after these corrections. No constraint, authorization boundary, skip condition, or concurrency assertion was weakened.

## Management-command smoke validation

Against disposable synthetic rows, the following passed:

- `bootstrap_owner` using an ephemeral noninteractive secret;
- synthetic Scene creation and `run_worker --once`;
- `quarantine_unfinished_jobs`;
- `enqueue_search_rebuild --dry-run` and `reset_search_projections --dry-run`;
- structured archive export and archive validation;
- portable archive restore to an empty target and `verify_restore_readiness`;
- legacy import staging/report plus import quarantine;
- AI-request quarantine;
- static production readiness;
- database/private-content readiness failing specifically before MFA enrollment evidence;
- database/private-content readiness passing after a synthetic WebAuthn/recovery-code fixture.

Worker readiness has no separate management command; worker execution and Job registry/readiness were exercised through the worker and production-readiness commands.

## Native and application restore rehearsal

`pg_dump -Fc` created a custom-format dump outside the repository. `pg_restore` restored it into a separately created empty `strange_novelty_restore_test` database. Applied migration state and non-null Scene current pointers were verified. Post-restore reconciliation invalidated sessions/assurance/challenges/pending recovery state, quarantined unfinished Jobs/imports/AI Requests, and reset derived search projections without starting a worker.

The restore target was then recreated empty to exercise the portable Workspace archive path with a synthetic pre-existing Account reference. UUID-preserving restore, revoked Grant policy, semantic report generation, and `verify_restore_readiness` passed. The dump, archive, report, databases, role, TLS material, credentials, logs, and synthetic import artifact were removed during cleanup.

## Final checks

The final PostgreSQL suite passed as above. Ruff lint and formatting, mypy, local/test/safe-production Django checks, deploy checks, migration drift, and `git diff --check` passed. Deploy checks retained only the deliberately conservative HSTS include-subdomains and preload warnings. Repository scans found no persistent secret, database URL, dump, database file, real email, private manuscript content, SQLite setting, production hostname, or weakened PostgreSQL skip.

## Cleanup and remaining blockers

Both disposable databases and the bounded test role were dropped. The repository-specific PostgreSQL cluster was stopped and removed, along with its socket and every temporary credential, certificate, dump, archive, report, command-output, and source fixture. No `TEST_DATABASE_URL` was persisted.

Remaining production blockers are operational rather than PostgreSQL application correctness:

- install `libpq-dev` in the controlled build environment and confirm locked `psycopg-c` production synchronization;
- perform real owner WebAuthn enrollment and protected secret injection;
- configure and exercise production backup scheduling/storage, monitoring, alert routing, and incident procedures;
- build/review the immutable image in its controlled environment;
- provision and validate the actual isolated production PostgreSQL roles/TLS/backup boundary;
- complete deployment approval and controlled launch procedures.

No cloud resource or deployment was created, and this validation does not mark those activities complete.
