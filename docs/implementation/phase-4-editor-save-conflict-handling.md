# Phase 4 Implementation Record: Editor Load, Save, and Conflict Handling

## Status

Completed on 2026-07-11.

This is an implementation record, not an ADR. ADR-0001 through ADR-0015 remain authoritative.

## Scope Delivered

Phase 4 provides the first private server-rendered Scene workflow: an authorized list, Scene creation, current-pointer editor load, explicit complete-content save, durable scoped save idempotency, retry reconciliation, and manual conflict presentation. It uses Phase 3 domain services and does not introduce an alternate mutation path.

No autosave, automatic merge, force save, browser draft store, generic Job system, search, import, AI, backup automation, MFA, deployment, public API, or frontend framework was added.

## Routes and View Responsibilities

| Route | Method | Responsibility |
| --- | --- | --- |
| `/scenes/` | GET | authorized non-trashed Scene list |
| `/scenes/new/` | GET, POST | creation form and Phase 3 creation service |
| `/scenes/<uuid>/` | GET | load explicit current Revision and editor/read-only view |
| `/scenes/<uuid>/save/` | POST | validate, idempotently mutate, or present a conflict |

All routes require login and resolve the current active owner Workspace on every request. Missing, inaccessible, cross-Workspace, revoked, trashed, and disallowed edit targets use non-disclosing 404 behavior. Browser-provided Workspace values are ignored.

## Scene List and Creation

The list orders through the Scene model's `(ordering, UUID)` order, includes active and clearly labeled archived Scenes, and excludes trashed Scenes. It displays title, lifecycle, and updated time but no manuscript content or history.

The creation form contains only a bounded title. POST invokes `create_scene()` with the server-authorized Workspace. The service allocates a sparse order inside its Workspace transaction: 1024 initially and 1024 above the current maximum thereafter. Successful creation returns HTTP 303 to the new editor. GET never creates data. Durable Scene-creation idempotency remains deferred; Post/Redirect/Get prevents normal refresh duplication but does not make uncertain creation retries safe.

## Editor Load Contract

The editor selects `Scene.current_revision` directly and renders:

- opaque Scene identity in its protected URL;
- current Revision UUID in a hidden precondition;
- current Scene version in a hidden precondition;
- title and lifecycle;
- escaped authoritative plain text;
- bounded revision/version status.

It never infers current content from timestamps or revision numbers. Active Scenes have a complete-content form. Archived Scenes expose escaped read-only text. Trashed Scenes return 404.

## Save Form and Mutation Contract

The POST form contains complete proposed text, expected current Revision UUID, expected Scene version, a client-carried bounded idempotency key, and the sole `explicit_save` intent. A tiny local progressive-enhancement script replaces the server fallback key with a browser-generated cryptographic UUID when supported. Saving remains fully usable without JavaScript.

The browser cannot set resulting revision identity/number, Scene version, operation identity, actor, Workspace, timestamps, or lifecycle. Django forms validate UUIDs, non-negative versions, key syntax, intent, and the Phase 3 content limit. Authoritative normalization remains exclusively the Phase 3 normalization function.

## Scene Save Request Schema

`SceneSaveRequest` contains:

- application-generated UUIDv4 primary key;
- protected Workspace, Account, and Scene references;
- bounded client idempotency key (16–128 allowlisted characters through the service/form);
- 64-character semantic request fingerprint;
- constrained pending, succeeded, conflicted, or failed-terminal state;
- bounded failure classification;
- optional protected successful Revision and resulting Scene version;
- created, completed, and updated timestamps.

Uniqueness is scoped to `(Workspace, Account, Scene, idempotency key)`. The row contains no manuscript content, title, raw body, arbitrary JSON, session/CSRF value, credential, exception, or log payload. It is deliberately narrower than ADR-0010's deferred general Idempotency Record.

## Fingerprint Inputs

The deterministic SHA-256 fingerprint covers canonical JSON containing:

- Scene UUID;
- expected current Revision UUID;
- expected Scene version;
- SHA-256 of Phase 3 normalized proposed content;
- explicit-save intent.

The normalized content itself is never stored in the request record. Matching keys with different fingerprints return a 409 conflict and cannot mutate the Scene.

## Transaction and Locking Model

`save_scene_content()` first normalizes and fingerprints the request. Within one outer PostgreSQL transaction it reauthorizes and locks the active Workspace/Grant boundary, locks the Workspace-scoped Scene, and locks or reserves the scoped request identity. Scene locking serializes same-Scene request reservations.

For a new request, the Phase 3 mutation service executes in a nested atomic block, rechecks lifecycle and both concurrency preconditions, appends one Mutation Operation and Revision, advances the pointer/version, and returns its result. The request row is marked succeeded with the resulting Revision/version before the outer transaction commits. A rollback therefore leaves neither a false success nor partial domain history.

An optimistic conflict rolls back the nested mutation savepoint, records only a conflicted request outcome, and commits no Revision or Mutation Operation. Pending rows are not ordinarily externally visible because reservation and completion share one transaction. Abnormal privileged/manual pending records require later operational cleanup policy.

## Retry and Uncertain Outcome Reconciliation

Every replay reauthenticates and reauthorizes before reading a result. An identical successful replay returns HTTP 303 to the editor and creates no new Revision or operation. An identical conflicted replay remains a conflict. A changed fingerprint returns 409. If the server committed but the browser lost the response, retrying the same semantic request and key reconstructs the committed result. This provides idempotent effect handling, not exactly-once delivery.

## Conflict Response and Manual Reconciliation

A concurrency mismatch returns HTTP 409 with an announced conflict message, escaped current authoritative content, and the escaped submitted draft retained only in the immediate response. The page offers a current-editor link and a new complete-content form carrying latest preconditions and a new request key. The owner can copy, edit, discard, or explicitly submit reconciled content.

There is no server conflict-draft row, automatic merge, force-save bypass, patch path, or silent overwrite. Manual reconciliation is a new ordinary mutation and preserves all prior immutable Revisions.

## Lifecycle Behavior

Active Scenes are editable. Archived Scenes remain visible and are read-only. Trashed Scenes are excluded from the ordinary list and inaccessible through editor/save routes. Lifecycle transitions remain deferred.

## HTTP Semantics

- successful creation/save: HTTP 303 Post/Redirect/Get;
- invalid semantic form: HTTP 422 with escaped submitted values/errors;
- optimistic or key-fingerprint conflict: HTTP 409;
- oversized request envelope: HTTP 413;
- malformed content length: HTTP 400;
- inaccessible/disallowed private target: HTTP 404;
- unauthenticated request: safe local login redirect;
- GET to save: HTTP 405;
- CSRF failure: Django's protected HTTP 403 behavior;
- unexpected errors: generic production handling.

Domain correctness remains in services and transactions rather than status codes.

## Privacy, Caching, and Logging

Every private response uses Django `never_cache`, producing private/no-store behavior. Manuscript content is confined to protected request/response bodies and authoritative Revisions; it is absent from URLs, idempotency rows, logs, metrics, and errors. Templates escape titles and text. No analytics, CDN, external script, font, or tracker was added. Scene models remain absent from writable admin.

## Accessibility and Progressive Enhancement

The workflow is keyboard-usable and server-rendered. Forms have explicit labels, linked error summaries, field errors, semantic status/alert regions, and text descriptions that do not depend on color. Current and submitted conflict text have distinct headings and labels. The local UUID enhancement affects only request-key generation; all list, create, edit, save, validation, and conflict behavior works without JavaScript.

## Migration Created

- `src/scenes/migrations/0002_scenesaverequest.py`

It creates only `SceneSaveRequest`, protected foreign keys, bounded fields, one scoped uniqueness constraint, state/failure/version checks, and a Workspace/Scene/time index. It contains no data operation or later-phase model. `makemigrations --check --dry-run` reports no drift.

The migration was not applied because no explicit safe `TEST_DATABASE_URL` was configured. SQLite was not used.

## Tests Added

Database-free tests cover routes, forms, hidden preconditions, key validation, stable/sensitive fingerprints, exact privacy-minimized schema, bounded choices, narrow migration contents, accessible templates, and progressive key generation.

PostgreSQL-only tests cover authentication/authorization/revocation, Workspace/list isolation, lifecycle filtering, CSRF, 303 creation, editor pointer selection and escaping, archived/trashed behavior, complete normalization, dual preconditions, conflict non-mutation, identical replay, changed-key semantics, replay authorization, simulated response loss, rollback, manual reconciliation, cross-Workspace denial, malformed/oversized input, and concurrent identical-request convergence.

Phase 4 adds 12 database-free cases and 23 PostgreSQL-only cases. With no `TEST_DATABASE_URL`, the complete repository suite reports 58 passed and 52 PostgreSQL cases skipped. The integration tests skip rather than use SQLite.

## Verification Commands

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

## Known Limitations and Deferred Work

- Scene creation does not yet have durable idempotency.
- There is no autosave, local/server draft persistence, unsaved-navigation warning, or client request queue.
- There is no automatic diff or merge; comparison is two labeled text areas.
- General idempotency retention/cleanup awaits Phase 6 policy.
- Lifecycle transition UI/services are absent.
- Password login remains without required production MFA.
- Phase 5 Security Events and broader audit boundaries remain deferred.
- Jobs, search, backup automation, import, AI, and production deployment remain later phases.

## ADR Relationship

This implementation preserves ADR-0001 through ADR-0015: Django mediates every private operation; PostgreSQL remains authoritative; Workspace authorization is server-resolved; Scene Revision remains the sole immutable body; saves use complete normalized content and dual optimistic preconditions; idempotency is not authority; conflicts never silently overwrite or merge; rendered text is escaped; browser state remains non-authoritative; and all later subsystems remain outside this phase.
