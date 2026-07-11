# Phase 2 Implementation Record: Account, Authentication, and Workspace Bootstrap

## Status

Completed on 2026-07-11.

This record describes implementation and does not amend ADR-0001 through ADR-0015.

## Scope Delivered

Phase 2 adds the minimum password-authenticated owner and Workspace authorization foundation needed before private Scene work:

- explicit Workspace and Workspace Grant records;
- centralized current-grant authorization helpers;
- a one-time atomic owner bootstrap command;
- normalized-email login and POST-only logout;
- database-backed Django session use and private landing behavior;
- accessible server-rendered authentication templates;
- correct Account administration forms and registration;
- migrations and PostgreSQL-only integration-test coverage.

MFA, recovery, session inventory, Scenes, Jobs, search, import, AI, backup automation, and production deployment remain unimplemented.

## Workspace Schema

`Workspace` is the private authorization root and contains no manuscript content.

| Field | Definition |
| --- | --- |
| `id` | application-generated UUIDv4 primary key; no integer identity |
| `name` | human-readable label, maximum 200 characters |
| `is_active` | bounded activation state, defaults active |
| `created_at` | timezone-aware creation timestamp |
| `updated_at` | timezone-aware update timestamp |

The database rejects an empty name. Deletion from grants and bootstrap evidence uses `PROTECT`. Workspace UUIDs remain locators, not authority, and are not displayed on the landing page.

## Workspace Grant Schema

`WorkspaceGrant` explicitly relates one Account to one Workspace.

| Field | Definition |
| --- | --- |
| `id` | application-generated UUIDv4 primary key |
| `account` | protective foreign key to the custom Account |
| `workspace` | protective foreign key to Workspace |
| `role` | constrained Version 1 role |
| `state` | `active` or `revoked` |
| `revoked_at` | required for revoked grants; absent for active grants |
| `created_at` | timezone-aware creation timestamp |
| `updated_at` | timezone-aware update timestamp |

Constraints enforce one active Account/Workspace grant and consistent state/revocation timestamp. Composite indexes support current-grant lookups by Account or Workspace. Revoked grants remain evidence and do not authorize access.

## Role Choice

The only implemented role is `owner`. No member/editor placeholder was added because Version 1 has one human owner and no collaboration workflow. Future role vocabulary requires explicit product and authorization review rather than silently assigning meaning to a reserved value.

Staff, superuser, email, session, UUID possession, and object references do not grant Workspace authority.

## Authorization Services

Views use `workspaces.services` rather than issuing raw Grant queries.

- `resolve_owner_workspace(account)` resolves the one active Workspace through an active owner Grant on every protected landing request.
- `get_authorized_workspace(account, workspace_id)` resolves a named Workspace only when Account, Workspace, role, and Grant state all match.

Both helpers require an authenticated active Account, require an active Workspace and active owner Grant, and raise the same `Http404` outcome for missing, inaccessible, revoked, inactive, or ambiguous state. Browser/session identifiers are always revalidated against PostgreSQL. Grant revocation therefore takes effect on the next request without session expiry.

## Bootstrap Completion Record

`OwnerBootstrap` is narrow singleton completion evidence for the explicit initial-owner operation. It contains:

- one fixed non-secret UUID primary key used only to serialize/deduplicate the initial operation;
- protective one-to-one Account and Workspace references;
- completion timestamp.

It contains no password, password hash copy, email copy, token, secret, manuscript content, or arbitrary metadata. It is created by the command, never by migration or startup.

## Bootstrap Command

`python manage.py bootstrap_owner` requires explicit `--email` and `--workspace-name`.

Interactive operation:

- normalizes and validates email;
- trims and validates the Workspace name;
- checks for existing bootstrap/application state before requesting a password;
- reads and confirms the password through `getpass` hidden input;
- applies Django's configured password validators before mutation;
- atomically creates exactly one Account, Workspace, active owner Grant, and completion record;
- prints only bounded success/already-complete text.

`--no-input` is available only through an ephemeral environment variable named by `--password-env`; the password is never a CLI argument. Exact reruns return an already-complete outcome without reading or resetting a password. Changed email/name fails visibly. Existing unrelated Account, Workspace, or Grant state blocks bootstrap rather than being silently attached. A fixed singleton key plus unique constraints cause concurrent duplicate attempts to roll back safely.

The migrations contain no owner data or `RunPython` bootstrap operation.

## Login and Logout

Login uses Django's authentication backend and a project form whose login field is email. `AccountManager.get_by_natural_key()` normalizes the complete submitted address before lookup. Invalid credentials, inactive Accounts, and unknown Accounts use the same message.

Django's login operation rotates/cycles the session identifier. The login view accepts only Django-validated local `next` destinations; unsafe external destinations fall back to the private Workspace landing. There is no remember-me control.

Logout uses Django's POST-only `LogoutView`, requires CSRF through middleware, flushes the current session, and redirects to login. GET cannot terminate a session.

Password login is an interim Phase 2 boundary. ADR-0005 still requires MFA before real private content is introduced.

## Session, Cookie, and Cache Behavior

- sessions remain database-backed;
- session cookies remain HttpOnly and SameSite `Lax`;
- CSRF cookies are HttpOnly and SameSite `Lax` for server-rendered forms;
- sessions expire when the browser closes; unlimited remember-me is absent;
- production settings require Secure cookies and protected transport;
- Django's login/logout primitives provide session fixation protection and current-session invalidation;
- Workspace authority is not stored solely in session state;
- the root and Workspace landing use `never_cache`; private responses contain no-store/private-revalidation directives.

Session inventory, all-session revocation, recent-authentication state, MFA elevation, recovery sessions, and explicit idle/absolute duration values remain deferred.

## Minimal Private UI

The project provides:

- `/login/` with labeled email/password controls, CSRF, autocomplete hints, and a generic `role="alert"` error summary;
- `/logout/` as a form POST from the private page;
- `/workspace/` with only “Workspace ready,” the escaped Workspace name, and a statement that Scene features are absent;
- `/` redirecting based on authentication state.

Templates contain no JavaScript, trackers, external fonts, CDNs, raw UUID display, environment details, package versions, or private content.

## Account Administration

The Account is registered with a project-owned `UserAdmin` configuration using custom creation/change forms bound to `Account`. Forms use email and supported Django password widgets/handling; no username field appears. Identity/timestamp fields are read-only where appropriate, and raw passwords are never displayed.

Admin remains operational tooling. It does not create Workspace Grants automatically, bypass authorization helpers, or imply creative authority. No superuser was created.

## Security Event Decision

No Security Event model was added. ADR-0005 and ADR-0014 establish event meaning, but exact physical schema, event vocabulary ownership, correlation representation, retention, access, indexes, restoration behavior, and failure coupling remain deferred. Creating a Phase 2-only generic metadata table would risk an unbounded sensitive audit payload and conflict with Phase 5's planned evidence-boundary work.

Bootstrap uses bounded command output, and login/logout use Django behavior without logging credentials or submitted email. Security Event persistence must be added before production readiness and before claiming the complete ADR-0005 audit boundary.

## Login-Throttling Decision

No throttle is claimed or implemented in Phase 2. The accepted architecture requires rate limiting, but:

- Django's local-memory cache is per-process and not dependable across web processes;
- Redis and an external rate-limit service are outside scope;
- a database-backed throttle needs a reviewed privacy-safe key/fingerprint, retention, cleanup, concurrency, and restoration design;
- raw emails and IP addresses must not become logs or metric labels.

The login endpoint is isolated behind one form/view boundary so a later reviewed throttle can wrap it. Generic failures reduce enumeration but do not provide brute-force resistance. Password-only login must not protect real private content before MFA and rate limiting are implemented.

## Migration Created

- `src/workspaces/migrations/0001_initial.py`

It creates only `Workspace`, `WorkspaceGrant`, and `OwnerBootstrap`, with UUID identities, protective relationships, indexes, and constraints. It depends on the custom Account migration. It contains no data operation, owner, credentials, Scene, Job, search, import, AI, backup, or security-event table.

`makemigrations --check --dry-run` reports no changes. The migration was not applied because no explicit safe `TEST_DATABASE_URL` or local PostgreSQL credentials were configured. SQLite was not used.

## Tests Added

Non-database Phase 2 tests cover:

- UUID and protective relationship metadata;
- owner-only role/state choices;
- constraint/index definitions;
- Account admin form bindings and absence of username;
- generic login messages;
- POST-only logout route configuration;
- centralized query scoping and non-disclosing denial;
- private/no-store Workspace rendering without UUID display;
- root redirect behavior;
- migration models and absence of data operations.

PostgreSQL integration tests are present for:

- normalized email login and private landing;
- generic invalid/inactive failures;
- session rotation;
- POST-only logout/session invalidation and CSRF;
- safe and rejected external redirects;
- login-required/private caching behavior;
- missing/revoked/cross-Workspace/staff-only denial;
- grant uniqueness/state constraints;
- atomic, idempotent, conflicting, and partial-failure bootstrap;
- password hashing and output secrecy.

Without `TEST_DATABASE_URL`, the full suite reports 35 passed and 14 PostgreSQL integration tests skipped. The integration tests do not fall back to SQLite and will run unchanged against an explicitly configured safe PostgreSQL test database.

## Commands and Verification

Commands include:

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

Database-free settings/migration checks use reserved `.invalid` PostgreSQL hosts and do not apply migrations.

## Security and Privacy Checks

- no committed credentials, owner data, working hostnames, tokens, keys, private content, or manuscript material;
- no password CLI argument, output, logging, migration, or duplicate verifier storage;
- production cookie/transport settings remain fail-closed;
- login errors remain generic and redirects use Django's host/scheme validation;
- logout is POST-only and CSRF-protected;
- Workspace authorization rechecks active grant state on every private request;
- staff/superuser status alone never authorizes Workspace access;
- private responses are non-cacheable and templates escape values;
- no SQLite, Redis, external scripts, trackers, or later-phase model was added;
- bootstrap is explicit, transactional, idempotent, and absent from startup/migrations.

## Deliberately Deferred Work

- WebAuthn, TOTP fallback, MFA enforcement, recovery codes, and recovery workflows;
- compromised-password screening beyond configured Django validators;
- login throttling/rate limits and Security Event persistence;
- session inventory, remote/all-session revocation, recent authentication, and explicit expiry durations;
- password change/reset and email notification;
- invitations, collaboration, additional roles, and Workspace administration UI;
- Scene, Scene Revision, Mutation Operation, lifecycle, ordering, editor, and content behavior;
- Jobs, search, backup/restore automation, import, AI, workers, frontend enhancement, and deployment.

## ADR Relationship

- ADR-0001/0002: Django remains the server policy boundary and HTML baseline; the browser receives no database authority.
- ADR-0003: Workspace authorization and sessions use PostgreSQL only; constraints reinforce service rules.
- ADR-0004: stable UUID possession grants no authority; Scene concurrency remains deferred.
- ADR-0005: local password Account, database sessions, CSRF, generic errors, explicit bootstrap, and grant authorization are implemented; MFA, recovery, throttling, session review, and recent authentication remain outstanding.
- ADR-0006: no manuscript/editor content was introduced.
- ADR-0007/0008: Account, Workspace, and Grant are distinct with direct explicit relationships and native UUIDs; no creative domain tables were added.
- ADR-0009/0010: restore/session reconciliation, Jobs, and idempotency records remain later work.
- ADR-0011/0012/0013: AI, search, and import remain absent.
- ADR-0014: environment separation, protected production cookies, bounded health/UI output, and no secret logging are preserved; Security Event schema is deferred explicitly.
- ADR-0015: login/logout use private server-rendered POST/CSRF/redirect/cache semantics without adding a public API or frontend framework.
