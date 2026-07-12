# Phase 5 Implementation Record: Security Events and Audit Boundaries

## Status

Completed on 2026-07-11.

This record documents implementation. ADR-0001 through ADR-0015 remain authoritative.

## Scope Delivered

Phase 5 adds a dedicated, privacy-bounded Security Event subsystem; server-generated request correlation; selected bootstrap, authentication, authorization-denial, and Scene-conflict evidence; read-only operational administration; and explicit failure-coupling rules. Existing immutable Mutation Operations remain the sole accepted creative-mutation provenance.

No Job, Job Attempt, generic Idempotency Record, worker, scheduled cleanup, external telemetry, MFA, search, import, AI, backup automation, deployment, frontend framework, event sourcing, Redis, or SQLite feature was added.

## Evidence Boundaries

| Record/channel | Meaning | Explicit exclusions |
| --- | --- | --- |
| Scene Revision | immutable complete manuscript history | security/access outcomes |
| Mutation Operation | provenance for an accepted domain mutation | login, denial, conflict, execution state |
| Scene Save Request | durable deduplication and save outcome | creative provenance and general security audit |
| Security Event | bounded security-relevant fact | manuscripts, requests, credentials, arbitrary metadata |
| operational log | short-lived diagnosis/classification | durable audit authority and private payloads |
| future Job Attempt | execution-attempt evidence | not implemented; never substituted by Security Event |

None grants authorization merely by identity or reference.

## Security Event Schema

`SecurityEvent` contains:

- application-generated UUIDv4 primary key;
- bounded event type and outcome;
- immutable occurred timestamp and creation timestamp;
- optional protected Account actor;
- optional protected Workspace;
- bounded target category and optional UUID target reference;
- 32-character lowercase hexadecimal correlation identifier;
- bounded web/operator service role;
- bounded reason classification.

The model contains no text/JSON payload, title, email input, password/hash, session/CSRF value, IP address, user agent, query, prompt, filename/path, exception, stack trace, request body, or URL field. Database checks constrain every taxonomy field and the correlation shape. Indexes support type/time, outcome/time, Workspace/time, and actor/time review.

## Event Taxonomy

Phase 5 event types are:

- `owner_bootstrap_succeeded`;
- `owner_bootstrap_rejected`;
- `login_succeeded`;
- `login_failed`;
- `logout_succeeded`;
- `workspace_access_denied`;
- `scene_access_denied`;
- `scene_save_conflict`;
- `scene_save_key_conflict`.

Outcomes are `succeeded`, `denied`, `conflicted`, and `failed`. Targets are authentication, account, session, Workspace, Scene, and bootstrap. Service roles are web and operator. Reasons are none, invalid credentials, inaccessible, inactive grant, optimistic concurrency, idempotency-key reuse, existing state, and invalid input.

Unknown and inactive-account login failures deliberately have no Account or Workspace reference. Inaccessible Workspace/Scene events omit the browser-supplied target UUID. Known authorized Scene save conflicts may retain the Scene UUID because scope has already been resolved.

## Correlation Model

`RequestCorrelationMiddleware` runs immediately after Django security middleware. It generates a fresh UUIDv4 hexadecimal value per request and always replaces browser-supplied `X-Request-ID` input so a caller cannot encode private identifiers in operational evidence. The safe value is attached to the request and returned in the response header. Internal service boundaries still validate correlation shape before persistence.

Correlation carries no Account, Workspace, title, content, email, session, or semantic data. It grants no access and is not selected as a metric label. No tracing vendor is required.

## Recording Service API

`record_security_event(SecurityEventSpec, required=False)` accepts only typed enum values, resolved Account/Workspace objects, an optional UUID target, and validated correlation. It performs no serialization and has no arbitrary detail parameter.

An optional event database failure returns `None` after emitting only the constant operational classification `security_event_recording_failed` with service role and safe correlation in protected log-record fields. It never logs the exception body or recursively creates another event. `required=True` re-raises after the same bounded log classification.

## Transaction and Failure Coupling

- Bootstrap success evidence is required and inserted in the same transaction as Account, Workspace, Grant, and OwnerBootstrap. Event failure rolls the entire bootstrap back.
- Bootstrap rejection evidence uses a separate best-effort short write because no authoritative bootstrap is accepted.
- Login, logout, and access-denial events are best-effort short writes. Evidence failure cannot grant access or disclose credentials.
- Scene concurrency evidence is written inside the Scene Save Request transaction after the nested authoritative mutation savepoint has rejected the stale write.
- Scene idempotency-key conflict evidence is written inside the locked save-request transaction before returning the conflict.
- Successful ordinary Scene saves use Mutation Operation provenance and do not also create a redundant Security Event.
- Replayed successful/conflicted save requests return prior outcomes without duplicating their original evidence.

Phase 5 does not add event-on-event-failure recursion or claim that operational logging is durable audit evidence.

## Bootstrap Integration

The first successful bootstrap records a required event referencing the created Account, Workspace, and fixed bootstrap target UUID. Exact idempotent reruns create no duplicate event. Conflicting existing state creates a bounded conflicted rejection event; invalid password-policy input creates a bounded failed rejection event. Passwords, hashes, secret values, and submitted email text are absent.

## Login and Logout Integration

Successful login records the known Account and its resolved active Workspace. Unknown, invalid-password, and inactive-account failures retain the identical generic UI and record only `login_failed` plus `invalid_credentials`, with no attempted email or fabricated actor. Successful authenticated POST logout captures the known actor/Workspace before Django flushes the session, then records a session-category event without retaining any session identifier.

## Workspace and Scene Denial Integration

The Workspace landing and all Scene routes record bounded denial evidence when current authorization resolution fails. Staff/superuser flags remain irrelevant. Cross-Workspace, revoked, missing, inactive, and trashed targets continue to use non-disclosing 404 behavior. Denial events use generic inaccessible reasons and omit untrusted target identifiers and private labels.

## Scene Conflict Integration

An optimistic conflict records `scene_save_conflict` with the authorized actor/Workspace/Scene and `optimistic_concurrency`. Idempotency fingerprint mismatch records `scene_save_key_conflict` and `idempotency_key_reuse`. Neither event stores the key, fingerprint, current/submitted content, title, or request body. Neither creates a Revision or Mutation Operation.

## Mutation Operation Boundary

Mutation Operation remains limited to accepted Scene creation and accepted complete-content revision, with protected actor, Workspace, Scene, bounded type/source, and timestamp. Its instance save/delete and default QuerySet update/delete paths reject mutation. No login, logout, denial, conflict, or Security Event type was added to it.

## Immutability Protections

Security Event and Mutation Operation reject instance updates, ordinary deletes, and default QuerySet update/delete operations. Historical Account, Workspace, and Scene relationships use `PROTECT`. Neither has a user-facing editing route. Database triggers remain deferred.

Privileged SQL, database ownership, custom migrations, raw cursors, or alternate managers remain residual bypasses until production database-role separation and operational controls are implemented.

## Read-Only Administration

Security Event and Mutation Operation have staff-only view permission in Django admin and no add, change, or delete permission. Broad lists expose only bounded taxonomy/source/time columns. Account/Workspace/target/correlation identifiers are omitted from list columns; necessary identifiers remain available only on protected detail pages. No manuscript field exists in either model. Admin remains operational tooling, not Workspace authority.

## Operational Logging Boundary

Phase 5 uses Python/Django logging only for the constant security-event-write failure classification. Permitted record extras are bounded event name, service role, and safe correlation ID. No custom vendor/framework was added, and complete observability is not claimed.

Routine logging remains prohibited from containing manuscripts, titles, login input, credentials, cookies, session/CSRF values, request bodies, save keys/fingerprints, or private exception bodies. Security Events remain distinct from logs.

## Retention and Cleanup

Security Events require bounded operational/security retention, but exact periods remain deferred. Mutation Operations remain durable domain provenance and follow domain-history retention. Expiring Security Events must never delete Revisions, Mutation Operations, or save requests. No purge command, scheduled cleanup, worker, or retention field was added. Backup/archive/restoration treatment follows later phases.

## Migration Created

- `src/security_events/migrations/0001_initial.py`

It creates only Security Event, UUID identity, bounded columns, protected optional references, checks, and indexes. It has no data operation, arbitrary payload, content, credential/session field, or later-phase table. Migration drift reports no changes.

The migration was not applied because no explicit safe `TEST_DATABASE_URL` was configured. SQLite was not used.

## Tests Added

Database-free tests cover exact schema/exclusions, taxonomy, correlation generation/validation/middleware, service validation and bounded logging failure, instance immutability, read-only admin, and narrow migration contents.

PostgreSQL-only tests cover protected references, QuerySet immutability, login success/failure privacy, logout/session flushing, atomic bootstrap evidence and rollback, quiet exact rerun, conflict evidence, revoked/cross-Workspace denial, Scene concurrency/key conflicts without domain provenance, and successful save/replay separation.

Phase 5 adds 9 database-free cases and 13 PostgreSQL-only cases. With no `TEST_DATABASE_URL`, the complete repository suite reports 67 passed and 65 PostgreSQL cases skipped. Integration cases skip rather than use SQLite.

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

## Known Limitations

- No exact Security Event retention period or cleanup mechanism exists.
- Login throttling, alerting, metrics, tracing, and SIEM integration remain absent.
- Optional event failures can leave missing denial/authentication evidence; they never weaken the underlying authorization result.
- Correlation remains process/request evidence rather than a distributed trace.
- Admin inspection depends on Django staff access and later production operational controls.
- Database-level append-only triggers are not used.
- Security Event archive/restoration handling awaits backup work.

## Deferred Phase 6 and Later Work

Phase 6 will add generic durable idempotency, Job/Attempt state, worker leases, retries, cancellation, dispatch, retention, and recovery reconciliation without collapsing those records into Security Events or Mutation Operations. MFA/recovery, search, backup automation, import, AI, deployment, external telemetry, and cleanup scheduling remain later work.

## ADR Relationship

This implementation preserves ADR-0001 through ADR-0015: Django authorizes private operations; PostgreSQL stores bounded durable evidence; Security Events never grant authority or contain manuscripts; creative provenance remains Mutation Operation; save deduplication remains Scene Save Request; future execution evidence remains separate; correlations are non-semantic; administration is not creative authority; and logs stay privacy-minimized.
