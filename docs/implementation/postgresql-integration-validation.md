# PostgreSQL Integration Validation

## Status and execution boundary

Validation was attempted on 2026-07-11 from the repository workspace. No production, shared, remote, development-authoritative, or unknown database was contacted. No real private data, legacy repository data, working credential, cloud resource, or deployment was used.

The PostgreSQL execution portion is **blocked**, not passed. `TEST_DATABASE_URL` was unconfigured; local TCP and standard Unix-socket readiness probes found no reachable PostgreSQL server; local `initdb`/`pg_ctl` server-control tools were unavailable; and neither Docker nor Podman was available as the permitted disposable fallback. The safety policy therefore prohibited creating a database or attempting administrator discovery. No unrelated databases or roles were enumerated.

## Environment discovery

| Capability | Result |
| --- | --- |
| Project virtual environment | available, CPython 3.14 |
| Project-local uv at discovery | available, version locked by repository workflow |
| `TEST_DATABASE_URL` | unconfigured |
| Local PostgreSQL TCP listener | unreachable |
| Local PostgreSQL standard socket | unreachable |
| PostgreSQL client tools | available, PostgreSQL 16.14 |
| `pg_dump` / `pg_restore` | available, PostgreSQL 16.14 |
| Local server-control tools | unavailable |
| PostgreSQL C development header | unavailable (`pg_config.h`) |
| Docker / Podman | unavailable |

PostgreSQL 16.14 above is the **client-tool version only**. No server version was available and none is claimed.

## Dependency validation

`uv lock --check` passed. `uv sync --locked` successfully restored the locked default development groups, including the binary Psycopg test implementation. `uv sync --locked --all-groups` was attempted and failed specifically while building locked `psycopg-c` 3.3.4 because the host lacks PostgreSQL development headers. The dependency lock was not changed. This is an expected host prerequisite distinction: tests use `psycopg-binary`; the production image/build environment must provide controlled libpq headers/tooling.

## Migration and schema validation

Database migration execution from zero, `showmigrations` applied-state evidence, SQL introspection, constraint execution, index inspection, protective deletion execution, and restored-schema comparison were blocked because no safe PostgreSQL server existed.

Database-free migration drift validation completed: `makemigrations --check --dry-run` reported no changes. Local and test Django checks passed with a reserved `.invalid` PostgreSQL target and never fell back to SQLite. Existing static migration/model tests exercised the declared custom Account-first dependency, UUID fields, Workspace/Grant, Scene/Revision/Mutation Operation, Scene Save Request, Security Event, Job/Attempt/Idempotency, PostgreSQL search-vector/GIN declarations, import/provenance, AI, and MFA schemas. These results validate declarations only; they do not substitute for physical PostgreSQL outcomes.

Phase 8 remains migration-free as designed. No parallel integer identity or SQLite configuration was found by the static suite and repository scan. Physical foreign-key action and cross-table invariant verification remains pending.

## Test results

The complete suite ran without `TEST_DATABASE_URL`:

- 124 passed;
- 110 skipped, all PostgreSQL-dependent under the repository test boundary;
- 0 failed;
- final pytest-reported duration: 2.74 seconds.

Accordingly, **zero PostgreSQL-backed tests ran**. Authentication/Workspace, Scene/editor/idempotency, competing Job claims and leases, full-text search execution, archive/restore, legacy import application, fake-AI persistence, MFA persistence/throttling concurrency, and management-command mutation scenarios remain blocked. Their database-free schema, parser, service-boundary, template, command-registration, privacy, and configuration tests passed, but this report makes no integration claim for them.

## Operational command validation

Command discovery confirmed registration of `bootstrap_owner`, `run_worker`, `quarantine_unfinished_jobs`, `enqueue_search_rebuild`, `reset_search_projections`, `export_workspace_archive`, `validate_workspace_archive`, `verify_restore_readiness`, `report_legacy_import`, `quarantine_unfinished_imports`, `quarantine_unfinished_ai_requests`, and `verify_production_readiness`.

Static `verify_production_readiness --static --private-content` passed using bounded temporary production values and no database connection. Its database-backed/private-owner enrollment mode was not run. All other requested smoke operations require authoritative disposable rows or database state and were blocked; none was falsely executed against an unknown target.

## Backup, archive, and restore

`pg_dump` and `pg_restore` 16.14 were available, but there was no safe source database or second restore target. No dump was created, no archive artifact was written, and no restore was attempted. Application archive and restore integration likewise remained blocked because it requires synthetic authoritative records in PostgreSQL. Existing database-free archive parser/hash/path/scope tests passed. No backup artifact remains.

## Safe checks completed

- locked dependency metadata check and locked development synchronization;
- attempted locked production-group synchronization with the missing-header failure preserved;
- full database-free pytest suite;
- local and test Django checks;
- safe temporary production static readiness and deploy checks;
- migration drift check;
- management-command registration check;
- Ruff lint and format, mypy, `git diff --check`, and repository safety scans (completed in final verification).

The deploy check reported only the existing conservative HSTS include-subdomains and preload warnings. No production readiness or deployment completion is inferred.

## Defects and repository changes

No implementation defect was established because the database integration path could not run. No test was weakened, skipped, or changed, and no application code, dependency version, migration, ADR, or prior implementation record was modified. This report and a checklist status note are the only repository changes.

## Cleanup

No database, role, container, dump, archive, restored target, temporary credential, or source artifact was created, so no database/container teardown was required. Temporary production values existed only in process environments. The repository contains no resulting URL, password, database file, backup, or private fixture.

## Exact prerequisites for completion

Provide one of the following before rerunning this phase:

1. an explicitly documented disposable local `TEST_DATABASE_URL` whose host is localhost, `127.0.0.1`, or a local Unix socket and whose database name is clearly test-only; or
2. an already-running local PostgreSQL administrator boundary authorized to create the bounded `strange_novelty_test_runner` role and `strange_novelty_test`/restore databases; or
3. an already-installed Docker/Podman runtime supported for an ephemeral local PostgreSQL container.

For production dependency validation, install the deployment-controlled PostgreSQL/libpq development headers needed by locked `psycopg-c`. These prerequisites must not be satisfied by production credentials, an unknown server, SQLite, or invented test results.

## Remaining production blockers

- complete migration-from-zero and physical schema validation on disposable PostgreSQL;
- all 110 PostgreSQL integration tests, including concurrency and full-text execution;
- disposable application archive/restore and `pg_dump`/`pg_restore` rehearsal;
- database-backed management-command smoke checks and MFA-owner readiness fixture;
- production dependency build in the controlled image environment;
- the still-open operational, backup, monitoring, enrollment, and deployment checklist items.
