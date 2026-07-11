# Phase 0 Implementation Record: Repository and Development Foundation

## Status

Completed on 2026-07-11.

This is an implementation record, not an ADR. Accepted ADR-0001 through ADR-0015 remain authoritative.

## Selected Foundation

| Area | Selection |
| --- | --- |
| Python | CPython 3.14, latest 3.14 micro release; project constraint `>=3.14,<3.15` |
| Django | Django 5.2 LTS, `>=5.2.14,<5.3` |
| Dependency and environment tool | uv with PEP 735 dependency groups and committed `uv.lock` |
| PostgreSQL driver | Psycopg 3; base `psycopg`, binary implementation for local/test, C implementation for production |
| Tests | pytest with pytest-django; PostgreSQL integration tests required once Django exists |
| Lint and format | Ruff |
| Static type checking | mypy with pragmatic checks; no claim of complete Django typing |
| Project package | `strange_novelty` under `src/` |
| Initial Django apps | `accounts`, `workspaces`, and `scenes` |

No frontend toolchain, container system, CI service, deployment platform, monitoring vendor, or cloud service was selected.

## Dependency Boundaries

- Core project dependencies contain Django and Psycopg's provider-independent Python package.
- `lint`, `test`, and `typing` groups isolate quality tooling.
- `dev` includes those three groups and is the default local environment.
- `test` includes `psycopg-binary` for self-contained local/test client support.
- `production` includes `psycopg-c` for a deployment-controlled, locally linked implementation.

The lockfile records resolved versions. Updating constraints and upgrading the lockfile are explicit reviewable actions.

## Intended Layout

Phase 1 will create the Django project package and apps only after reviewing the custom Account and first-migration boundary:

- `src/strange_novelty/`: settings, URL configuration, and process entry points;
- `src/accounts/`: custom Account and authentication integration;
- `src/workspaces/`: Workspace and Workspace Grant;
- `src/scenes/`: Scene, Scene Revision, Mutation Operation, and initial domain services;
- `tests/`: synthetic unit, PostgreSQL integration, migration, HTTP, and later worker tests.

Package directories are not created in Phase 0 so they cannot be mistaken for initialized Django application code.

## Deferred to Phase 1 or Later

- exact PostgreSQL server version within Django 5.2's supported range;
- UUIDv7 library and UUIDv4 fallback implementation;
- settings-module decomposition and configuration-loading library or code;
- custom Account fields, authentication identifier, manager, and `AUTH_USER_MODEL` implementation;
- model, table, field, index, and constraint names;
- initial migration decomposition and reviewed SQL;
- exact database roles, connection pooling, transport, timeouts, and production topology;
- WebAuthn/TOTP packages and all authentication policy values;
- worker, search, backup, import, AI, frontend, editor, and deployment packages;
- CI, containers, production artifact, secret manager, and telemetry systems.

The custom Account model remains a hard gate: it must exist before the first Django migration is created or executed.

## ADR Alignment

- ADR-0001 and ADR-0014: configuration examples contain placeholders only; secrets, production data, browser authority, and deployment concerns remain outside Phase 0.
- ADR-0002: the selected supported CPython/Django LTS toolchain prepares the server-rendered modular monolith without initializing it.
- ADR-0003 and ADR-0008: Psycopg 3 and PostgreSQL-only testing preserve the accepted database boundary; no SQLite workflow is introduced.
- ADR-0004 through ADR-0007: the intended `accounts`, `workspaces`, and `scenes` layout reflects accepted identity, authorization, revision, content, and domain boundaries without implementing them.
- ADR-0009 through ADR-0013: recovery, Jobs, AI, search, and import remain later dependency groups and app-boundary decisions.
- ADR-0015: no frontend or public API toolchain is introduced; server-rendered HTML remains the later baseline.

## Verification Performed

Phase 0 verification covers:

- TOML parsing of `pyproject.toml`;
- uv dependency resolution, lock generation, and `uv lock --check` consistency;
- Ruff configuration discovery and empty-source validation without creating application code;
- `git diff --check`;
- review of changed files for secret/private-data patterns and example placeholders;
- repository inspection confirming no Django project, apps, models, migrations, database files, or application code were created;
- Git status review before committing only the Phase 0 files.

No dependencies were installed globally, no PostgreSQL connection or database command was attempted, Django was not initialized, and no migration command was run.
