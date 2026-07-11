# Development Setup

## Scope

This document describes the Phase 0 development foundation. Django has not been initialized, no application package exists, and no migrations or database commands should be run yet.

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

Phase 1 will implement and test configuration loading. Production configuration will be externally injected, production-only, validated at startup, and fail closed when required or unsafe values are missing.

## Quality Commands

After `uv sync --locked`:

```console
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy .
uv run --locked pytest
```

Until application source and tests exist, these commands primarily validate configuration and documentation-adjacent Python files if any are added. pytest may report that no tests were collected; Phase 1 will add the first application and migration tests.

Validate dependency metadata and the lockfile without changing them:

```console
uv lock --check
```

## Intended Django Layout

Phase 1 is expected to create:

```text
manage.py
src/
  strange_novelty/   # Project settings, URLs, process entry points
  accounts/          # Custom Account and authentication boundary
  workspaces/        # Workspace and Workspace Grant boundary
  scenes/            # Scene, Scene Revision, and Mutation Operation core
tests/
```

The exact settings-module split and later apps for Jobs, search, recovery, import, and AI remain deferred. The custom Account model must be defined before the first Django migration is created or run.

## Repository Safety

- Use synthetic test data only.
- Never copy production or Story Engine private data into this repository.
- Never commit `.env`, `private-data/`, databases, dumps, exports, backups, credentials, keys, certificates, manuscripts, or artwork.
- Do not modify `/home/burmuss/projects/the-story-engine`.
- Do not run migrations until Phase 1 establishes the custom Account model and reviewed initial migration sequence.
