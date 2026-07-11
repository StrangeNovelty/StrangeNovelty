# Phase 1 Implementation Record: Django and PostgreSQL Foundation

## Status

Completed on 2026-07-11.

This implementation record is not an ADR. ADR-0001 through ADR-0015 remain authoritative.

## Project Layout

The repository now uses an installable src-layout Python project:

```text
manage.py
src/
  strange_novelty/
    settings/
      base.py
      local.py
      test.py
      production.py
      environment.py
    urls.py
    asgi.py
    wsgi.py
  accounts/
    apps.py
    managers.py
    models.py
    migrations/0001_initial.py
  workspaces/
    apps.py
  scenes/
    apps.py
tests/
```

`setuptools` discovers packages under `src/`, and uv installs the project editable in the local environment. `workspaces` and `scenes` are installed app boundaries only; they contain no models or migrations.

## Settings Structure

- `base.py`: installed apps, middleware, templates, URLs, timezone-aware UTC behavior, static-file development boundary, custom Account selection, Django password validators, database-backed session engine, CSRF/session defaults, and common security headers.
- `local.py`: explicit PostgreSQL URL, safe local-only secret fallback, local hosts, and explicit/strict debug parsing.
- `test.py`: explicit PostgreSQL backend with clearly test-only defaults, UTC, no debug, and one supported fast password hasher for tests.
- `production.py`: required production environment marker, secret, database URL, hosts, HTTPS CSRF origins, secure cookies, HTTPS redirect, and bounded initial HSTS; unsafe or absent values raise `ImproperlyConfigured` without echoing values.
- `environment.py`: small standard-library parsing helpers for required values, strict booleans, comma-separated lists, and PostgreSQL URLs.

The WSGI and ASGI entry points default to production settings. `manage.py` defaults to local settings. No settings module falls back to SQLite.

## PostgreSQL Configuration Boundary

All application environments use `django.db.backends.postgresql`. Local development requires an explicit `DATABASE_URL`. Tests may override `TEST_DATABASE_URL`; the built-in default is synthetic and uses the reserved `postgresql.invalid` host so database-free checks cannot reach a real service. Production requires an explicit URL containing scheme, host, database name, username, and password.

No PostgreSQL service, database, role, or credentials were created. An early migration consistency check used the initial `127.0.0.1` test-only default, discovered an unrelated local PostgreSQL listener, and received an authentication rejection for the synthetic `test-only` account. It did not authenticate, query, create, or migrate data. The default was immediately changed to the reserved `.invalid` host to prevent future offline checks from contacting local services. Django then completed file/model comparison without a database.

## Custom Account Model

`accounts.Account` extends `AbstractBaseUser` and `PermissionsMixin`. It is selected by `AUTH_USER_MODEL` before the first migration.

Exact project-owned fields are:

| Field | Definition |
| --- | --- |
| `id` | UUID primary key, application-generated with `uuid.uuid4`, non-editable |
| `email` | unique Django `EmailField`; login identifier |
| `is_active` | boolean, defaults true |
| `is_staff` | boolean, defaults false; Django administration only |
| `date_joined` | timezone-aware timestamp, defaults to `timezone.now`, non-editable |
| inherited `password` | Django password hash storage |
| inherited `last_login` | nullable Django authentication timestamp |
| inherited `is_superuser` | Django administration permission flag |
| inherited `groups` and `user_permissions` | Django administration permission relationships |

`USERNAME_FIELD` is `email`; `REQUIRED_FIELDS` is empty because email is already the login argument. There is no username, profile, integer identity, Workspace relationship, MFA state, recovery state, or creative authorization field.

## Account Manager Behavior

`AccountManager`:

- rejects absent or whitespace-only email;
- applies Django email normalization, trimming, and full-address `casefold()` consistently;
- hashes passwords through `set_password()`;
- defaults ordinary accounts to non-staff and non-superuser;
- rejects a missing superuser password;
- defaults superusers to active, staff, and superuser;
- rejects any explicit false superuser invariant;
- saves using the manager's selected database alias;
- is serialized in migrations.

The string representation is the normalized email. It contains no password or secret. `is_staff` and `is_superuser` remain Django administration flags and do not grant Workspace or creative authority.

## UUID Choice

Phase 1 uses Python's supported `uuid.uuid4` with a native Django/PostgreSQL UUID primary key. It is dependable, requires no additional package, is generated before persistence, and satisfies ADR-0004's accepted fallback. UUIDv7 remains deferred until a supported implementation is selected and migration/operational behavior is justified. No parallel integer identity was added.

## Administration and URLs

The Django administration site is mounted for later operational tooling, but the custom Account is deliberately not registered in Phase 1. Correct custom Account creation/change forms and operational policy are deferred rather than reusing forms that assume Django's built-in username model. No Account or superuser was created. Future admin ability will not be Workspace authorization.

The root URL configuration exposes Django administration and `/health/`. The health response contains only `ok`; it does not inspect the database or reveal versions, configuration, topology, secrets, or private identifiers.

## Migration Created

- `src/accounts/migrations/0001_initial.py`

The initial migration creates the custom Account, UUID primary key, authentication/admin fields, permission relationships, and custom manager. It depends on Django auth migration `0012_alter_user_first_name_max_length` so inherited permission relationships are available.

`makemigrations --check --dry-run` reports no model changes. The migration was not applied because the repository had no `.env`, `DATABASE_URL`, or confirmed safe local PostgreSQL service. SQLite was not used.

## Tests Added

The 22 focused tests cover:

- test, local, and production settings imports;
- production failure when settings are absent, debug is true, hosts are wildcarded, or the database is not PostgreSQL;
- valid explicit production configuration import;
- PostgreSQL-only backend, UTC, and timezone-aware settings;
- `AUTH_USER_MODEL` selection;
- UUID primary-key assignment and field type;
- email normalization and missing-email rejection;
- ordinary and superuser manager behavior;
- superuser invariant failures;
- password hashing and verification without database persistence;
- Account string representation;
- initial migration contents/dependency;
- minimal health response;
- Django system checks.

Database application tests remain pending a confirmed local PostgreSQL test database. The Phase 1 suite intentionally patches Account persistence for manager tests rather than silently using SQLite.

## Commands and Verification

Commands run from the repository root included:

```console
uv sync --locked
python manage.py check --settings=strange_novelty.settings.local
python manage.py check --settings=strange_novelty.settings.test
python manage.py check --settings=strange_novelty.settings.production
python manage.py makemigrations --check --dry-run --settings=strange_novelty.settings.test
pytest
ruff check .
ruff format --check .
mypy manage.py src tests
git diff --check
```

Temporary synthetic environment values were supplied to local and production checks. They were not committed. The migration-check connection attempt and corrective `.invalid` default are documented above.

Verification results before commit:

- locked dependencies synchronized successfully;
- local, test, and production Django system checks reported no issues;
- migration consistency reported no changes after the initial migration was corrected to match inherited permission-field definitions;
- all 22 tests passed;
- Ruff lint and format checks passed;
- mypy passed for 23 source files;
- secret/private-data/SQLite/prohibited-model scans passed;
- `git diff --check` passed.

## Security and Privacy Checks

- Production configuration is explicit and fail-closed.
- Errors name invalid variables/categories but do not echo their values.
- No secret, working credential, private hostname, manuscript, database, dump, export, backup, or Story Engine content is committed.
- Session and CSRF cookies are HTTP-only and SameSite-constrained; production requires secure cookies and protected transport.
- The browser receives no database credentials.
- The health response is bounded and non-sensitive.
- Account administration flags do not implement Workspace authority.
- The password tests confirm hashing rather than raw storage.
- No SQLite dependency or settings fallback exists.

## Deferred Phase 2 and Later Work

- owner bootstrap and creation of the first Account/Workspace/Grant;
- project-owned Account administration forms and reviewed admin registration;
- login, logout, authentication views, and user-facing forms;
- WebAuthn, TOTP fallback, recovery codes, recent authentication, and session review/revocation;
- password policy values and compromised-password screening;
- rate limiting, security-event persistence, and emergency recovery;
- Workspace/Grant models and authorization services;
- Scene, Scene Revision, Mutation Operation, lifecycle, ordering, and domain services;
- PostgreSQL role/grant creation, connection pooling, production topology, and migration execution;
- UUIDv7 implementation selection;
- Jobs, search, backup/restore automation, import, AI, editor, frontend enhancement, and deployment.

## ADR Relationship

- ADR-0001/0002: Django is the policy boundary in a server-rendered modular monolith; no client framework or direct database access was added.
- ADR-0003: every environment is configured for PostgreSQL and timezone-aware UTC operation; no SQLite fallback exists.
- ADR-0004: the Account uses a stable application-generated UUID; Scene concurrency work remains deferred.
- ADR-0005: a project-owned minimal Account supports later authentication without prematurely implementing MFA, recovery, sessions UI, or Workspace authority.
- ADR-0006/0007: `scenes` and `workspaces` exist only as module boundaries; no premature domain tables were created.
- ADR-0008: the custom Account exists before the first migration; the UUIDv4 fallback is used; only the Account migration was created.
- ADR-0009 through ADR-0013: backup, Jobs, AI, search, and import remain unimplemented.
- ADR-0014: environment separation, validation, safe production settings, UTC, health, and secret boundaries are established without deployment infrastructure.
- ADR-0015: templates and private session/CSRF foundations are ready, but no editor or mutation route was implemented.
