# Development Setup

## Scope

This document describes the local development foundation through Phase 1. The Django project and custom Account migration exist, but no migration has been applied because no safe local PostgreSQL configuration was available during Phase 1 verification.

## Selected Toolchain

- CPython 3.14, using the latest available 3.14 micro release.
- Django 5.2 LTS, constrained to `>=5.2.14,<5.3`.
- uv for Python acquisition, virtual environments, dependency groups, and `uv.lock`.
- Psycopg 3 (`psycopg`), with `psycopg-binary` in local/test environments and `psycopg-c` for the eventual production build.
- pytest and pytest-django for tests.
- Ruff for formatting, imports, and linting.
- mypy for pragmatic static checks. Complete Django typing and a Django-specific plugin are deferred until the project/settings package exists.

The official Django 5.2 release notes designate 5.2 as an LTS release and support Python 3.14 in current 5.2 patch releases. Psycopg documents Python 3.14 support and distinguishes binary development installation from locally linked production builds. uv provides a committed cross-platform lockfile and standardized dependency groups.

## Install the Development Tool

Install uv through an official supported method for the workstation. Do not install project dependencies globally.

Confirm it is available:

```console
uv --version
```

uv reads `.python-version`, obtains a compatible CPython 3.14 interpreter when permitted, and creates the project-local `.venv`.

## Create the Local Environment

From the repository root:

```console
uv sync --locked
```

The default `dev` group includes the lint, test, and typing groups. It also includes Psycopg's binary implementation so local setup does not require system `libpq` headers.

Useful group-specific sync commands are:

```console
uv sync --locked --only-group lint
uv sync --locked --only-group test
uv sync --locked --only-group typing
uv sync --locked --no-default-groups --group production
```

The production group selects `psycopg-c`, which must build against deployment-controlled `libpq` and toolchain packages. That group is an interface for later production packaging; Phase 0 does not build or deploy it.

## Local Configuration

Copy `.env.example` to `.env` and replace every placeholder with environment-specific local values. `.env` is ignored by Git.

The example intentionally contains no working credentials. PostgreSQL is required for application and integration-test work; SQLite must not be introduced as an authoritative or convenience substitute.

The settings modules validate configuration at import/startup. Production configuration is externally injected, production-only, and fails closed when required or unsafe values are missing. The production settings require an explicit secret key, PostgreSQL URL with credentials, non-wildcard allowed hosts, HTTPS CSRF trusted origins, `STRANGE_NOVELTY_ENV=production`, and `DJANGO_DEBUG=false`.

## Quality Commands

After `uv sync --locked`:

```console
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy .
uv run --locked pytest
```

The Phase 1 suite exercises settings validation, the Account model and manager, migration contents, the minimal health URL, and Django system checks without connecting to PostgreSQL.

Validate dependency metadata and the lockfile without changing them:

```console
uv lock --check
```

## Intended Django Layout

Phase 1 created:

```text
manage.py
src/
  strange_novelty/   # Project settings, URLs, process entry points
  accounts/          # Custom Account and authentication boundary
  workspaces/        # Workspace and Workspace Grant boundary
  scenes/            # Scene, Scene Revision, and Mutation Operation core
tests/
```

Settings are split into `base`, `local`, `test`, and `production`. Later apps for Jobs, search, recovery, import, and AI remain deferred. The custom Account model is present in `accounts/migrations/0001_initial.py`, before any migration has been applied.

## Django Settings and Checks

`manage.py` defaults to local settings. Commands may select another module explicitly:

```console
DJANGO_SETTINGS_MODULE=strange_novelty.settings.local uv run --locked python manage.py check
DJANGO_SETTINGS_MODULE=strange_novelty.settings.test uv run --locked python manage.py check
```

Local settings require `DATABASE_URL`. Test settings use a clearly test-only PostgreSQL URL with a reserved `.invalid` host so database-free checks cannot contact a real service. PostgreSQL integration tests require an explicit `TEST_DATABASE_URL`. Production process entry points default to `strange_novelty.settings.production` and fail closed without the required environment.

## PostgreSQL and Migrations

Once a dedicated local PostgreSQL database and synthetic-only test database exist, set local values without committing them:

```console
export DATABASE_URL='postgresql://<local-user>:<local-password>@<local-host>:<local-port>/<local-database>'
export TEST_DATABASE_URL='postgresql://<test-user>:<test-password>@<test-host>:<test-port>/<test-database>'
```

Then verify and apply migrations only to the intended local database:

```console
uv run --locked python manage.py check --settings=strange_novelty.settings.local
uv run --locked python manage.py makemigrations --check --dry-run --settings=strange_novelty.settings.local
uv run --locked python manage.py migrate --settings=strange_novelty.settings.local
```

Confirm the target before `migrate`. Do not run these commands against an unknown or production database, and never substitute SQLite.

Phase 3 adds `scenes/migrations/0001_initial.py`. The same `migrate` command applies Account, Workspace, Grant, Scene, Revision, and Mutation Operation migrations to the explicitly confirmed local PostgreSQL target. To run all PostgreSQL integration tests, set `TEST_DATABASE_URL` to a dedicated disposable test database before invoking pytest:

```console
export TEST_DATABASE_URL='postgresql://<test-user>:<test-password>@<test-host>:<test-port>/<test-database>'
uv run --locked pytest -m postgresql
```

The Phase 3 tests use synthetic text only. Do not use manuscript content as fixtures. Phase 3 provides domain services and no Scene HTTP route, form, template, or editor UI.

Phase 4 adds `scenes/migrations/0002_scenesaverequest.py`. Apply it only through the same confirmed local PostgreSQL migration command. After starting the local server, the private workflow is available at:

- `/scenes/` — authorized Scene list;
- `/scenes/new/` — Scene creation;
- `/scenes/<scene-uuid>/` — current Scene editor;
- `/scenes/<scene-uuid>/save/` — POST-only complete-content save.

To test conflicts manually, open one Scene in two tabs, save a synthetic change in the first tab, and submit a different synthetic change from the stale second tab. The second submission must show the submitted draft beside current saved content and must not overwrite it. Use only synthetic text during development.

Phase 4 has explicit save only. It has no autosave or browser draft persistence. Password login also remains an interim boundary without the required production MFA enforcement.

Phase 5 adds `security_events/migrations/0001_initial.py`. Apply it only to the same explicitly confirmed local PostgreSQL target. Authorized Django staff can inspect Security Events and Mutation Operations through read-only admin model pages; those pages do not grant Workspace authority and provide no add, change, or delete action.

Every HTTP response carries a server-generated random, non-semantic `X-Request-ID` correlation value. Browser-supplied correlation headers are always replaced so they cannot smuggle private identifiers into operational evidence. Correlation values are troubleshooting evidence, never authorization.

Phase 5 adds no Security Event cleanup schedule and no external logging, metrics, tracing, SIEM, or alerting service. Exact event retention remains an operational decision. Do not place private values in logs while testing event failure paths.

Phase 6 adds `jobs/migrations/0001_initial.py`. Apply it only to the explicitly confirmed PostgreSQL target. Run one bounded worker iteration with:

```console
uv run --locked python manage.py run_worker --once --settings=strange_novelty.settings.local
```

For local continuous execution, use `uv run --locked python manage.py run_worker --settings=strange_novelty.settings.local` in a separate terminal and stop it with Ctrl-C. This is a development process only; no production supervisor is configured.

After restoring an isolated database and before any worker starts, quarantine unfinished work with:

```console
uv run --locked python manage.py quarantine_unfinished_jobs --settings=strange_novelty.settings.local
```

The Version 1 queue is PostgreSQL-backed. There is no external broker, Redis, Celery, scheduled cleanup, or production worker supervision.

Phase 7 adds `jobs/migrations/0002_...` and `scenes/migrations/0003_scenesearchprojection.py`. After applying them to a confirmed PostgreSQL target, run the worker to build projections. The private search page is `/search/` and submits queries only through CSRF-protected POST bodies.

Enqueue a bounded rebuild without executing it:

```console
uv run --locked python manage.py enqueue_search_rebuild --workspace '<workspace-uuid>' --dry-run --settings=strange_novelty.settings.local
uv run --locked python manage.py enqueue_search_rebuild --workspace '<workspace-uuid>' --settings=strange_novelty.settings.local
```

After an isolated restore, quarantine unfinished Jobs first, then discard untrusted projections and explicitly enqueue replacements:

```console
uv run --locked python manage.py reset_search_projections --all-workspaces --confirm --enqueue --settings=strange_novelty.settings.local
```

Search is PostgreSQL full-text search only. There is no external, semantic, vector, embedding, recommendation, or AI retrieval system.

## Initial Owner Bootstrap

After applying migrations to a confirmed local PostgreSQL database, create the one initial owner and Workspace through the explicit interactive command:

```console
uv run --locked python manage.py bootstrap_owner \
  --email '<owner-email>' \
  --workspace-name '<workspace-name>' \
  --settings=strange_novelty.settings.local
```

The command requests and confirms the password through hidden terminal input. It never accepts a password argument or prints the password. Repeating the exact command after successful bootstrap reports that no changes were made; conflicting owner or Workspace values fail.

For controlled automation only, `--no-input` reads the password from the ephemeral environment variable named by `--password-env` (default `STRANGE_NOVELTY_BOOTSTRAP_PASSWORD`). Inject that value through protected process configuration, remove it immediately after use, and never place it in Git, `.env.example`, documentation, logs, or command arguments.

Do not use real private manuscript content yet. Phase 2 implements password login but deliberately does not enforce the WebAuthn/TOTP MFA boundary required by ADR-0005 before real private content is introduced.

## Local Authentication

Start the local development server only after confirming `DATABASE_URL` and applying migrations:

```console
uv run --locked python manage.py runserver --settings=strange_novelty.settings.local
```

Local routes are:

- `/login/` — normalized-email and password login;
- `/logout/` — POST-only logout from the authenticated Workspace page;
- `/workspace/` — minimal private Workspace landing page;
- `/admin/` — operational Django administration, not Workspace authority;
- `/health/` — bounded process-level response.

Login throttling, MFA, recovery, session inventory, remote session revocation, and Scene features are not implemented yet.

## Repository Safety

- Use synthetic test data only.
- Never copy production or Story Engine private data into this repository.
- Never commit `.env`, `private-data/`, databases, dumps, exports, backups, credentials, keys, certificates, manuscripts, or artwork.
- Do not modify `/home/burmuss/projects/the-story-engine`.
- Do not apply migrations until a dedicated local PostgreSQL target is explicitly configured and confirmed.
