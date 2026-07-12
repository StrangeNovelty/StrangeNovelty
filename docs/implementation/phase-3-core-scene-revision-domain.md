# Phase 3 Implementation Record: Core Scene and Revision Domain

## Status

Completed on 2026-07-11.

This record documents implementation. ADR-0001 through ADR-0015 remain authoritative.

## Scope Delivered

Phase 3 adds the authoritative Scene aggregate before any editor HTTP behavior:

- Workspace-scoped Scene, Scene Revision, and Mutation Operation models;
- active, archived, and trashed lifecycle values;
- sparse non-negative integer ordering;
- explicit current Revision and integer Scene version;
- deterministic normalized UTF-8 complete snapshots;
- atomic Scene creation with an empty initial Revision;
- atomic complete-content revision with dual optimistic-concurrency checks;
- explicit bounded domain errors and typed mutation results;
- layered Revision and Mutation Operation immutability;
- PostgreSQL constraints, indexes, migration, and integration tests.

No Scene view, form, template, editor, autosave, conflict UI, durable idempotency, Job, search, import, AI, Security Event, backup automation, MFA, or deployment feature was added.

## Scene Schema

| Field | Definition |
| --- | --- |
| `id` | application-generated UUIDv4 primary key; no integer identity |
| `workspace` | protective foreign key to Workspace |
| `title` | required trimmed plain label, maximum 200 characters |
| `lifecycle` | constrained `active`, `archived`, or `trashed`; defaults active |
| `ordering` | non-negative sparse `BigIntegerField` |
| `version` | non-negative `BigIntegerField`; physical default zero for controlled creation |
| `current_revision` | protective nullable foreign key to Scene Revision |
| `created_at` | timezone-aware creation timestamp |
| `updated_at` | timezone-aware update timestamp |

Scene stores no manuscript body. The current pointer is physically nullable only to resolve the circular creation/migration boundary. The ordinary creation service commits it non-null with version 1. Current content is never inferred from timestamps or maximum revision number.

Constraints require a non-whitespace title, valid lifecycle, non-negative order/version, and unique `(Workspace, ordering)`. The Workspace/lifecycle/order index supports the initial Scene collection.

## Scene Revision Schema

| Field | Definition |
| --- | --- |
| `id` | application-generated UUIDv4 primary key |
| `workspace` | protective direct Workspace foreign key |
| `scene` | protective Scene foreign key |
| `content` | one complete authoritative normalized plain-text snapshot |
| `content_sha256` | SHA-256 of normalized UTF-8 content, 64 lowercase hexadecimal characters |
| `revision_number` | positive Scene-scoped display/integrity number |
| `content_format_version` | exact `plain-text-v1` |
| `normalization_version` | exact `plain-text-nfc-lf-v1` |
| `base_revision` | optional protective predecessor in the same Scene/Workspace |
| `restored_from` | optional protective restoration source; restoration service deferred |
| `source` | bounded `owner` classification in Phase 3 |
| `actor` | optional protective Account attribution |
| `mutation_operation` | required protective one-to-one provenance operation |
| `created_at` | timezone-aware creation timestamp |

`(Scene, revision_number)` is unique and revision numbers must be positive. Format, normalization, and source values are database constrained. Indexes support descending Scene history and Workspace/time operations. There is no patch, current flag, rendered HTML, Markdown authority, editor JSON, search projection, AI payload, or mutable result field.

## Mutation Operation Schema

| Field | Definition |
| --- | --- |
| `id` | application-generated UUIDv4 primary key |
| `workspace` | protective Workspace foreign key |
| `operation_type` | `scene_created` or `scene_content_revised` |
| `source` | bounded `owner` classification |
| `actor` | optional protective Account reference |
| `scene` | optional protective Scene reference, populated by Phase 3 services |
| `created_at` | timezone-aware creation timestamp |

The operation contains no manuscript body, title copy, request body, password, session, prompt, error payload, arbitrary metadata, status stream, or secret. It records accepted provenance and is not event sourcing, a Security Event, or an Idempotency Record. Workspace/time and Scene/time indexes support bounded history queries.

## Lifecycle Decision

New Scenes are active. Ordinary complete-content mutation is allowed only while active. Both archived and trashed Scenes conservatively reject Phase 3 content mutation. Later lifecycle-transition services may define explicit restoration or archived-edit behavior without weakening current concurrency/provenance rules. Physical purge is absent.

## Ordering Decision

Scene ordering is a non-negative wide sparse integer scoped to Workspace. Phase 3 callers supply it explicitly; the service validates it and the database enforces uniqueness. No creation-time, UUID, title, or row order inference is used. Gap size, automatic allocation, rebalance, hierarchy scope, and reorder version semantics remain deferred.

## Version and Revision Numbering

Controlled Scene insertion starts transiently at Scene version 0 with a null pointer inside one transaction. The same transaction creates empty Revision number 1, assigns it current, and sets Scene version 1 before commit.

Each accepted content mutation:

- requires the observed current Revision UUID and Scene version;
- uses the current Revision number plus one;
- creates one new Revision;
- increments Scene version exactly once;
- makes the new Revision current.

Revision number is Scene-scoped display/integrity data, not identity. UUID remains identity. Current state is always the explicit pointer.

## Text Normalization

`normalize_scene_content()` implements normalization version `plain-text-nfc-lf-v1`:

1. require a Python `str` value;
2. reject embedded NUL characters;
3. reject values above 1,000,000 Unicode code points;
4. convert CRLF to LF, then remaining CR to LF;
5. apply Unicode NFC using the supported Python runtime;
6. preserve all other leading/trailing spaces, blank lines, punctuation, case, symbols, emoji, and ordinary Unicode exactly.

Empty content is valid. The service does not trim, reflow, transliterate, autocorrect, interpret Markdown/HTML, resolve URLs/paths, or execute templates/code. SHA-256 is computed over the normalized UTF-8 bytes and stored as integrity evidence, not authorization or authenticity.

## Domain Errors and Results

The service boundary distinguishes:

- `NotAuthenticated`;
- non-disclosing `SceneInaccessible`;
- `InvalidSceneTitle`;
- `InvalidSceneContent`;
- `InvalidSceneOrdering`;
- `LifecycleDisallowsMutation`;
- `OptimisticConcurrencyConflict`;
- `CrossWorkspaceReference`;
- `DomainIntegrityFailure`;
- immutable Revision/Mutation Operation failures.

Successful creation/mutation returns a frozen `SceneMutationResult` containing the committed Scene, Revision, and Mutation Operation.

## Scene Creation Transaction

`create_scene()`:

1. validates and trims the title, validates sparse order, and normalizes empty content;
2. requires an authenticated active Account;
3. resolves and then transaction-locks the active Workspace through a current active owner Grant;
4. inserts the Scene in controlled version-zero/null-pointer state;
5. inserts one `scene_created` Mutation Operation;
6. inserts empty Revision number 1 with exact format/normalization/hash/provenance;
7. assigns the pointer and version 1;
8. validates and commits every row atomically.

No signal, model save hook, startup action, or migration orchestrates these rows. Failure rolls back all three records. The service never logs content.

## Complete-Content Mutation Transaction

`revise_scene_content()` requires actor, Workspace UUID, Scene UUID, expected current Revision UUID, expected Scene version, complete proposed text, and a bounded content-revision intent.

Inside one transaction it:

1. normalizes the complete proposed text;
2. reauthorizes and locks the active Workspace/current Grant;
3. locks and reloads the Workspace-scoped Scene and current Revision;
4. rejects non-active lifecycle or inconsistent scope;
5. compares both expected Revision UUID and Scene version;
6. on mismatch raises `OptimisticConcurrencyConflict` before creating any row;
7. creates one `scene_content_revised` Mutation Operation;
8. creates one complete immutable Revision with `base_revision` equal to the prior current Revision;
9. advances the pointer and Scene version exactly once;
10. commits atomically.

There is no merge, force overwrite, patch, last-write-wins path, external call, or reliance on browser assertions. A sequential duplicate with the same old preconditions conflicts. Durable duplicate-delivery/idempotency safety is intentionally not claimed; the service signature and operation boundary can accept that later without changing revision semantics.

## Authorization Boundary

Phase 3 services consume the current Account and Workspace UUID but trust neither by possession. They reuse the Workspace authorization service, then recheck active Account, Workspace, owner Grant, and target Scene scope inside the transaction. Revocation therefore takes effect before mutation. Staff/superuser status is irrelevant.

Inaccessible Workspace and Scene state is represented by the same bounded service error. HTTP existence-disclosure mapping remains Phase 4.

## Immutability Enforcement

- Phase 3 services only insert Scene Revisions and Mutation Operations.
- Instance `save()` rejects every update after insertion.
- Instance `delete()` rejects ordinary deletion.
- Default managers return QuerySets whose `update()` and `delete()` reject mutation.
- All lineage, content, representation, hash, actor, operation, and timestamp fields are therefore append-only through ordinary application paths.
- Protective foreign keys prevent ordinary Scene/Workspace/Account deletion from cascading into history.
- Tests prove instance and QuerySet rejection and preservation of old content after new commits.

Residual risk remains: a database owner, privileged SQL, raw cursor, custom migration, or alternate manager can bypass Python protections. Database triggers are deferred under ADR-0008 because they complicate migration, repair, and restoration. Later least-privileged database roles and operational controls must restrict direct writes.

## Constraints and Known Database Limitations

PostgreSQL/Django constraints enforce row-local values, UUID/foreign-key existence, Scene ordering uniqueness, revision-number uniqueness, representation versions, and protective deletion.

PostgreSQL check constraints cannot safely validate arbitrary cross-row/cross-table equality. The following are enforced by transaction services and model `clean()` rather than a trigger:

- Scene current Revision belongs to that Scene and Workspace;
- Revision Workspace equals Scene Workspace;
- base/restored-from Revision belongs to the same Scene and Workspace;
- Mutation Operation scope matches Revision scope;
- every ordinary committed Scene has a non-null current pointer.

The nullable current pointer is physically necessary for circular creation, migration, restore, or repair. No public model-level convenience API commits an incomplete aggregate.

## Admin Decision

Scene, Scene Revision, and Mutation Operation are not registered in Django admin. A writable generic admin would bypass transaction, authorization, normalization, concurrency, lineage, and immutability services and could expose manuscript content. A future read-only operational interface requires a separate privacy/authority review.

## Migration Created

- `src/scenes/migrations/0001_initial.py`

It creates Scene, Mutation Operation, Scene Revision, the circular current pointer, protective foreign keys, UUID identities, indexes, and constraints. It depends on the custom Account and Workspace migrations. It contains no data migration, signal, bootstrap, sample content, integer identity, Job, search, import, AI, MFA, backup, or deployment table.

`makemigrations --check --dry-run` reports no changes. The migration was not applied because no explicit safe `TEST_DATABASE_URL` was configured. SQLite was not used.

## Tests Added

Database-free tests cover:

- UUID identities and exact schemas;
- absence of a Scene body field and forbidden operation payloads;
- lifecycle/order/version constraints and indexes;
- title/order validation;
- LF/NFC normalization, whitespace/Unicode preservation, empty content, NUL/type/limit rejection, and hash stability;
- instance immutability before database use;
- migration models and absence of data operations;
- protective references and no integer identities.

PostgreSQL-only tests cover:

- authorized atomic Scene/empty Revision/operation creation;
- revoked/unauthenticated denial and rollback;
- complete normalized mutations and preserved prior Revisions;
- both concurrency preconditions independently and together;
- competing stale writes and no last-write-wins;
- archived/trashed rejection;
- cross-Workspace denial;
- instance/QuerySet immutability;
- cross-scope lineage/current-pointer validation;
- unique ordering/revision and non-negative version constraints;
- complete-snapshot/no-idempotency semantics.

Without `TEST_DATABASE_URL`, the complete suite reports 46 passed and 29 PostgreSQL integration tests skipped (14 Phase 2 and 15 Phase 3). All integration tests run unchanged against a safely configured PostgreSQL test database; none falls back to SQLite.

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

Reserved `.invalid` hosts support database-free settings/migration checks without applying schema.

## Security and Privacy Checks

- every domain row has explicit Workspace scope and UUID identity;
- services reauthorize active Grant state inside transactions;
- staff/superuser status and UUID possession are ignored for domain authority;
- no content appears in Mutation Operations, logs, errors, URLs, templates, or sample fixtures;
- normalization rejects NUL/binary input and never executes content;
- no cross-record orchestration signal or automatic startup/migration data exists;
- history relationships are protective, not cascading;
- no Security Event, Idempotency Record, Job, search, import, AI, MFA, recovery, backup, worker, Redis, external provider, or deployment dependency exists;
- no Scene admin surface exposes or mutates manuscript content.

## Deliberately Deferred Phase 4 and Later Work

- Scene list/create/editor HTTP routes, forms, templates, CSRF mapping, and private cache behavior;
- explicit save payloads, conflict responses, manual reconciliation, and browser drafts;
- durable HTTP-save idempotency and duplicate-response reconciliation;
- autosave, multiple in-flight request handling, and editor accessibility;
- lifecycle-transition and reorder services;
- restoration service using `restored_from`;
- stronger same-Workspace composite database constraints or transparent triggers if later justified;
- read-only operational history/admin interface;
- Security Events, MFA/recovery/session inventory, Jobs, search, import, AI, backup automation, workers, and deployment.

## ADR Relationship

- ADR-0001/0002: domain authority remains in Django services; no browser or HTTP implementation was added.
- ADR-0003: PostgreSQL transactions, direct Workspace scope, constraints, and protective history implement the accepted persistence boundary.
- ADR-0004: distinct UUID Scene/Revision identity, full immutable snapshots, explicit pointer/version, dual optimistic concurrency, and no merge/last-write-wins are implemented.
- ADR-0005: services require current Account/Grant authorization; MFA remains required before real private content.
- ADR-0006: authoritative content is deterministic normalized UTF-8 plain text with explicit format/normalization versions and no rendered/editor authority.
- ADR-0007/0008: explicit relational Scene aggregate, Revision history, Mutation Operation provenance, initial empty Revision, sparse order, lifecycle, protective deletion, and physical migration sequence are implemented.
- ADR-0009/0010: integrity hashes support later verification, while backup, restoration, durable idempotency, and Jobs remain deferred.
- ADR-0011/0012/0013: AI, search, and import remain non-existent and cannot become authority.
- ADR-0014: no secrets/content telemetry or deployment infrastructure was introduced.
- ADR-0015: the domain save contract now exists for later HTTP adaptation; editor, CSRF, redirects, conflicts, and autosave remain Phase 4.
