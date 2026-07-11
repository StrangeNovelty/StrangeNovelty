# ADR-0008: Physical Schema, Constraints, and Initial Migration Boundary

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 physical Django/PostgreSQL schema direction and initial migration boundary, while exact Python, Django, PostgreSQL, UUID library, field and table names, field lengths, indexes, constraint names, initial numeric constants, sparse-order gap and rebalance values, lifecycle labels, provenance metadata shape, database roles, deferrability choices, migration operations, bootstrap mechanism, backup tooling, and deployment details remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; Django, PostgreSQL, authentication, authorization, data integrity, migration, backup, archive export, restoration, and operational perspectives

## Context

ADR-0007 establishes the logical core: Account, Workspace, Workspace Grant, Scene, and Scene Revision are distinct relational concepts; shared PostgreSQL tables are explicitly Workspace-scoped; Scene is the mutable aggregate root; Scene Revision is immutable content history; lifecycle, ordering, and provenance are separate concerns; and supporting records grant no authority merely by reference.

This ADR translates that logical model into a physical schema direction before Django initialization can create durable defaults. It must be concrete enough that a later implementation can define models and reviewed migrations without silently reopening identity, nullability, circular relationships, Workspace integrity, revision immutability, lifecycle, ordering, or recovery behavior.

The accepted decisions remain controlling:

- the browser is untrusted;
- Django application/query services are the policy boundary;
- PostgreSQL is authoritative for structured relational state;
- every private operation is authenticated, authorized, Workspace-scoped, and revalidated server-side;
- stable application identity uses the accepted UUID strategy;
- Scene and Scene Revision identities are distinct;
- Scene Revision is immutable append-oriented full-snapshot history;
- Scene current-revision pointer plus integer version protects current state;
- saves use optimistic concurrency and one atomic revision-plus-pointer transaction;
- failed or stale saves create no authoritative revision;
- no silent last-write-wins or automatic merge is permitted;
- Scene Revision alone stores authoritative normalized UTF-8 plain-text body content;
- Scene stores mutable aggregate metadata but no second authoritative body;
- direct Workspace identity appears on aggregate roots and important history records;
- PostgreSQL constraints reinforce but do not replace Django authorization and domain rules; and
- application implementation remains unauthorized while this ADR is drafted.

No production Strange Novelty database exists. The initial migrations may therefore establish correct foundations without compatibility hacks for earlier Strange Novelty tables. The old Story Engine is untrusted future import material and must not shape primary-key compatibility or schema layout.

The physical design must distinguish:

- logical model from physical schema;
- application identity from database primary key;
- UUID generation from UUID storage;
- Account from Workspace Grant;
- authentication fields from creative domain state;
- Scene from Scene Revision;
- current-revision pointer from revision lineage;
- Scene integer version from revision number;
- empty Scene from Scene with empty saved content;
- nullable creation-state pointer from corrupted missing pointer;
- lifecycle state from deletion timestamp;
- ordinary trash from physical purge;
- title from identity;
- ordering value from identity;
- created timestamp from ordering;
- provenance fields from security events;
- provenance operation from idempotency operation;
- authoring-source category from Canon authority;
- database constraints from application authorization;
- database immutability enforcement from administrator capability;
- Django migrations from handwritten operational-repair SQL;
- migration dependency ordering from domain dependency;
- backup from export;
- restoration from migration;
- legacy import from same-archive restoration; and
- initial schema choices from later performance tuning.

Exact Python, Django, PostgreSQL, UUID library, ordering library, deployment version, field names, field lengths, table names, index names, constraint names, and operational SQL remain undecided unless this ADR must identify a semantic field boundary.

## Decision

If accepted, Version 1 will use the following physical-schema direction.

1. Define a project-owned custom Django Account model before the first migration. It contains the supported authentication identity boundary but no Workspace creative state; complete login fields and MFA/session schemas remain later work.
2. Use native PostgreSQL UUID-compatible Django fields as physical primary keys for the narrow core: Account, Workspace, Workspace Grant, Scene, Scene Revision, and Mutation Operation. Generate IDs in trusted application code before persistence using ADR-0004's preferred UUIDv7 or required UUIDv4 fallback.
3. Create explicit Workspace and Workspace Grant tables. Grant directly references Account and Workspace and supports one active owner-level grant per Workspace in Version 1 without making staff/superuser status authoritative.
4. Create explicit Scene and Scene Revision tables. Scene stores direct Workspace scope, mutable aggregate metadata, lifecycle, sparse integer order, non-negative integer concurrency version, operational timestamps, and a current-revision pointer. It stores no body content.
5. Scene Revision stores direct Workspace and Scene references, complete normalized UTF-8 plain text, content-format and normalization versions, a Scene-scoped positive revision number, predecessor/base/restoration-source relationships, a Mutation Operation reference, authoring-source category, creation time, optional actor attribution, and optional bounded integrity metadata.
6. Every newly created Scene receives an explicit empty initial Scene Revision in the same creation transaction. A successfully committed ordinary Scene therefore always has a non-null current revision and version representing that initial content state.
7. The physical current-revision field may be nullable during staged migration, circular creation, isolated restoration, or repair sequencing. Ordinary application services must never commit or expose a new active Scene with a null pointer. Null means incomplete construction or invalid/restoration state, not an ordinary empty Scene.
8. Store current revision only on Scene. Do not add a mutable current flag to Scene Revision or infer current state from time or revision number.
9. Start Scene version at a documented non-negative initial value and advance it for content saves and every Scene mutation that can invalidate an editor's safe-save assumptions: current-revision change, title/organizational context change, lifecycle change, and reorder or parent move. Metadata changes that are explicitly proven irrelevant may later use a separate policy; they do not create Scene Revisions unless content changes.
10. Use Scene-scoped monotonically increasing revision numbers for display and integrity, unique with Scene, while stable UUID remains portable revision identity. The first empty revision receives the first display number.
11. Use a constrained lifecycle status column for likely active, archived, and trashed current states, plus transition timestamps only where they add operational meaning. Restoration is a transition; purge is not a retained status.
12. Use a wide sparse integer ordering column scoped to the initial Scene collection. Allocate gaps for ordinary insertion/reordering; exact gap size and rebalance policy remain implementation configuration. Do not use an external fractional-ordering package.
13. Create a narrow immutable Mutation Operation table in the initial core. It identifies Workspace, source category, optional Account/service attribution, operation time, and bounded source/reference metadata. Scene Revision references it. Idempotency records remain distinct supporting records.
14. Put common immutable source fields on Scene Revision even when an operation record exists: authoring-source category and actor/operation references needed to interpret the revision without event replay. Do not store manuscript bodies in provenance.
15. Enforce same-Workspace and same-Scene invariants with composite uniqueness and foreign-key structures where PostgreSQL supports them reliably. When Django cannot declare a needed composite foreign key cleanly, use a reviewed explicit migration operation rather than dropping the invariant.
16. Use protective deletion behavior for Account grants, Workspace, Scene, Scene Revision, Mutation Operation, current-pointer, and lineage relationships. Ordinary trash never cascades physical deletion of revisions.
17. Enforce ordinary revision immutability through service design, restricted update/delete paths, database privileges where practical, and tests. Do not require triggers initially. Any later trigger must be transparent structural enforcement and accommodate migrations/restoration explicitly.
18. Use Django migrations as the primary schema mechanism. Review generated operations and resulting SQL. Use explicit database migration operations only for constraints Django cannot safely express. Handwritten operational-repair SQL is not the primary migration system.
19. Sequence foundational migrations to avoid circular dead ends: Account; Workspace and Grant; Mutation Operation; Scene base without final current-pointer integrity; Scene Revision; current-revision relationship; same-Workspace/lineage constraints; lifecycle/order/version constraints; bootstrap boundary.
20. Bootstrap creates the initial owner, Workspace, and owner grant through a protected deployment/management workflow after schema migration. Passwords, secrets, recovery material, and owner-specific data never appear in migrations.
21. PostgreSQL row-level security is not required by this ADR. Supporting subsystem schemas for MFA, sessions, recovery, jobs, search, AI, import, export, backup, and restoration remain later decisions.

## Physical Schema Principles

The physical schema uses explicit concrete tables, native relational columns, and foreign keys for identity, Workspace scope, current pointers, lineage, lifecycle, ordering, and common provenance. Arbitrary JSON and generic foreign keys are not substitutes for relationships whose integrity matters.

Each core table uses a stable application-generated UUID as its physical primary key. This makes database primary identity and portable application identity the same value for the narrow core, eliminating a second identity namespace and accidental exposure of sequences.

Repeated Workspace columns are controlled redundancy. A child/history row carries Workspace to make authorization scope visible and to support composite integrity, export, restoration, and future partitioning. Constraints and services must prevent disagreement with the parent.

Physical schema choices express durable correctness, not premature performance tuning. Indexes required to support primary keys, uniqueness, and foreign keys follow from constraints; additional query/performance indexes require later evidence.

Nullability expresses a real state, not implementation convenience, except where staged circular creation or migration requires a physically nullable pointer whose ordinary service invariant is stricter. Such exceptions must be documented, testable, and detectable by integrity checks.

## Account Model Boundary

A custom project-owned Django Account model is established before the first migration and configured as the application's swappable authentication model from the beginning. Replacing Django's default user model after dependent migrations would be disproportionately difficult and would couple future Workspace grants to an avoidable legacy boundary.

The Account table uses a native UUID primary key generated before persistence. It contains only the authentication/account fields required by Django's supported model contract and later accepted login policy. It does not contain Workspace title, creative content, current Scene, Canon authority, or other domain state.

This ADR does not decide:

- exact username, email, or login identifier policy;
- complete field list or manager implementation;
- password hashers or validators;
- WebAuthn, TOTP, recovery, or session tables;
- staff/admin interface configuration; or
- exact account lifecycle columns beyond the ability to disable authentication without deleting Workspaces.

Account disablement blocks ordinary authentication but does not cascade to Workspace, Grant history, Scene, or revision deletion. Workspace Grant represents domain access; staff/superuser flags remain framework administration only.

Foreign keys needing actor attribution should normally reference Account explicitly when the actor is a human account. Generic actor references are rejected as the default. Service attribution uses a bounded category or future service-identity relation rather than pretending a job is a human Account.

## Workspace Table

Workspace is an explicit table with:

- native UUID primary identity;
- mutable display name or equivalent non-secret label;
- any narrowly justified enabled/lifecycle value;
- creation and update timestamps for operations; and
- no global-singleton assumption.

Workspace is the root foreign-key target for private core records. A Workspace ID conveys no authority.

Deletion is protective. Ordinary Account deletion or grant revocation cannot remove the Workspace. Workspace archival, trash, export, backup, restoration, ownership transfer, and physical purge require later policy and cannot be implemented as a casual cascade.

Exact display field length, Workspace lifecycle representation, uniqueness of display names, and purge semantics remain undecided. Display names are mutable and need not be globally unique.

## Workspace Grant Table

Workspace Grant is an explicit table with:

- native UUID primary identity because grants may be independently audited/revoked;
- direct Account foreign key;
- direct Workspace foreign key;
- constrained grant state;
- a Version 1 owner-level semantic marker or equivalent constrained representation;
- creation and optional revocation timestamps;
- optional creation-operation/source reference; and
- operational timestamps only where they add meaning.

Version 1 permits one active owner-level grant per Workspace and avoids a general role marketplace. The database should enforce uniqueness of the active owner relationship using supported uniqueness/conditional structures where feasible, while Django services enforce the allowed transition and current authorization.

The grant foreign keys use protective deletion behavior. Account disablement or grant revocation is not physical Account/Workspace deletion. Historical grant evidence must not disappear through an ordinary cascade.

Exact future role vocabulary, invitation state, teams, multiple owners, transfer, grant-retention period, and conditional-constraint syntax remain outside this ADR.

## Scene Table

Scene is an explicit mutable aggregate table with:

- native UUID primary identity;
- direct Workspace foreign key;
- mutable title/label;
- constrained lifecycle status;
- explicit sparse integer ordering value;
- non-negative integer optimistic-concurrency version;
- current Scene Revision foreign key;
- creation and update timestamps; and
- later parent/organizational references only when their schema is accepted.

Scene stores no authoritative body-content column, editor JSON, HTML, Markdown AST, search text, excerpt, or current-content cache treated as authority.

The current-revision foreign key is physically introduced after Scene Revision exists. It is nullable at the database field level for circular construction, staged restoration, and migrations, but ordinary creation commits an initial revision and non-null pointer atomically. An integrity query must detect null pointers outside explicitly controlled incomplete states.

The Workspace foreign key is protective. Ordinary trash changes lifecycle status; it does not delete the row. Current-revision deletion is protected. Scene physical deletion cannot cascade to revisions in ordinary application paths.

Title is not unique identity. Timestamps do not determine ordering or current revision. Exact title length, default order gap, timestamp precision, parent collection, and physical column names remain later implementation details.

## Scene Revision Table

Scene Revision is an explicit append-oriented table with:

- native UUID primary identity;
- direct Workspace foreign key;
- direct Scene foreign key;
- complete normalized UTF-8 plain-text content in a PostgreSQL text-compatible column;
- constrained content-format version;
- constrained normalization version;
- positive Scene-scoped revision number;
- predecessor revision reference;
- base revision reference;
- optional restoration-source revision reference;
- direct Mutation Operation reference;
- constrained authoring-source category;
- optional Account actor reference where a human performed the mutation;
- creation timestamp;
- optional bounded integrity metadata; and
- no mutable current flag.

Predecessor identifies the revision previously current when this revision committed. Base identifies the revision the initiating editor/operation observed. For ordinary saves they should match. Restoration source identifies the older revision whose content was deliberately copied into the new snapshot.

Lineage references use protective deletion behavior. They are nullable only where their semantics permit: the initial revision has no predecessor/base; ordinary later revisions require applicable lineage; non-restoration revisions have no restoration source.

Revision number is a display/integrity sequence unique within Scene. It is not identity, authorization, current selection, or a substitute for lineage. Allocation occurs inside the accepted transaction and must be safe against concurrent saves.

Revision rows are insert-only through ordinary services. Their Workspace, Scene, content, versions, lineage, operation, source category, actor, number, time, and integrity metadata cannot be edited in place through ordinary application paths.

Exact integrity algorithm, actor nullability for services/migrations, format-version physical type, normalization-version physical type, and source-specific references remain later work.

## Provenance and Mutation Operation Boundary

Version 1 creates a narrow Mutation Operation table immediately because revisions need a stable common record explaining the authorized mutation without overloading Scene Revision fields or waiting for every future subsystem.

The operation table contains logically:

- native UUID primary identity;
- direct Workspace foreign key;
- constrained operation/source category;
- optional Account actor foreign key;
- bounded service/source attribution where no human Account is the direct executor;
- creation timestamp;
- optional idempotency-operation reference added when that subsystem exists;
- optional source-record references added through typed later schemas; and
- bounded versioned metadata only where relational columns cannot yet represent non-authoritative detail.

It contains no manuscript body, prompt body, AI response body, password, session, token, recovery material, or arbitrary security-event payload. It is not a generic domain-event stream and current state is never reconstructed by replaying it.

Scene Revision retains common direct provenance fields—source category, actor where applicable, and operation reference—so a snapshot remains interpretable without event replay. The operation provides shared attribution and a stable junction for future import items, AI suggestions, restoration runs, migrations, repairs, and idempotency.

Provenance operation and idempotency operation remain distinct. Provenance explains source and authorized production; idempotency deduplicates one requested effect. Their relationship may be one-to-one or many-to-one under later subsystem rules, but neither grants permission.

Typed import, AI, restoration, migration, repair, job, export, backup, and security tables remain later schemas. Arbitrary unversioned JSON is not the sole provenance model.

## UUID Primary-Key Strategy

Core authoritative tables use native PostgreSQL UUID columns through Django's UUID-compatible field as physical primary keys.

UUID generation and storage remain separate concerns:

- trusted application code generates the ID before persistence;
- the preferred generator is UUIDv7 when a maintained supported implementation satisfies ADR-0004;
- UUIDv4 is the accepted fallback if UUIDv7 support is unavailable, immature, or operationally unclear;
- PostgreSQL stores the UUID value natively regardless of selected generation version; and
- canonical text serialization is an external format, not the database column type.

Integer primary keys plus separate UUID application IDs are not selected for the narrow core because they create two identities, extra uniqueness/indexes, ambiguity in foreign keys, and risk of sequence exposure without demonstrated performance need. Mixed strategies are avoided unless a future high-volume supporting table provides evidence.

Character columns containing UUID strings are rejected because they waste space, weaken validation, complicate indexing, and duplicate native support.

UUIDv7 order does not determine creation time, Scene order, revision order, current revision, or authority. Created timestamps and Scene-scoped revision numbers remain separate.

## Empty Scene and Current-Revision Nullability

Version 1 selects explicit empty initial content: creating a Scene also creates an immutable initial Scene Revision whose authoritative content is the normalized empty string.

The creation service:

1. generates Scene, Revision, and Mutation Operation UUIDs before persistence;
2. starts one transaction;
3. inserts the operation;
4. inserts the Scene in a controlled construction state with a null pointer if insertion order requires it;
5. inserts revision number one with empty normalized content and initial lineage semantics;
6. sets Scene current revision and initial integer version; and
7. commits only if every invariant succeeds.

Failure rolls back every row. An ordinary created Scene therefore never commits as a no-revision Scene. An empty Scene means a Scene whose current revision contains the empty string, not a missing revision.

The physical pointer remains nullable initially because the circular Scene-to-current-Revision and Revision-to-Scene relationship must support Django migration sequencing, transaction construction, isolated restoration, and controlled repair. Null is not ordinary domain state. Query/application invariants fail closed on an unexpected null pointer, and integrity checks report it.

The alternative—no revision until first save—reduces creation writes but creates two ordinary content-state models, complicates editor tokens, export, restoration, counts, and authorization, and makes null ambiguous. The explicit initial revision is selected for uniformity.

A future reviewed explicit database mechanism may tighten nullability after proving a safe deferrable circular insertion/restoration approach. This ADR does not require a trigger or deferred non-null assertion.

## Scene Version and Revision Number

Scene integer version is the mutable aggregate concurrency counter. Revision number is a display/integrity sequence for immutable content snapshots. They are not interchangeable.

The initial Scene receives a documented non-negative version when its empty revision becomes current. The exact numeric starting value is an implementation constant selected before migration, but all code and archives must treat it consistently.

Scene version advances on:

- every successful content save/current-revision change;
- restoration of an older content snapshot as a new current revision;
- lifecycle changes that affect whether editing is permitted;
- title or organizational-context changes presented as part of an editor's safe-save assumptions;
- reordering or parent moves where the editor token represents aggregate state; and
- approved administrative/migration mutations that change authoritative Scene state.

Changes proven not to affect the Scene aggregate may later use separate records without advancing the counter. This exception must be explicit; silently inconsistent version semantics are prohibited.

Metadata-only changes do not create Scene Revisions because those revisions represent body-content snapshots. They still advance the Scene version where listed and create appropriate operation/provenance evidence.

Revision numbers begin with the initial empty revision and increase by one for each committed Scene Revision. The database enforces uniqueness of `(Scene, revision number)` and positivity/non-negativity as selected. Allocation happens in the save transaction; gaps caused by rolled-back operations are acceptable if later implementation cannot guarantee contiguity without risk, but committed order and lineage must remain unambiguous.

Neither counter is inferred from row count or timestamps.

## Lifecycle Columns and Constraints

Scene uses one constrained current lifecycle column. Version 1 likely values are active, archived, and trashed. Exact serialized labels are selected before implementation and protected through application choices plus a database check constraint or equivalently strong constrained representation.

Relevant timestamps may include archived-at and trashed-at only if they are needed for operational review, retention, or recovery. They explain transitions but do not replace current status. Contradictory timestamps/status combinations are validated by services and, where PostgreSQL can express row-local rules safely, check constraints.

Restored is an operation/transition from archived or trashed to active (or another later allowed state), not necessarily a permanent current status. The operation/provenance record and timestamps explain it.

Purge is not stored as an ordinary lifecycle value on a retained Scene. Physical purge is a separately authorized future workflow with retention, backup, provenance, dependent-record, and security-event rules.

Multiple independent booleans are rejected because they permit contradictory state. Separate archive/trash tables are not selected initially because they complicate current authorization and ordering without a demonstrated history requirement.

Workspace lifecycle remains minimal until Workspace archival/deletion policy is decided. Account active/disabled state remains authentication state, not Scene lifecycle.

## Ordering Column Strategy

Scene uses a wide sparse integer ordering column scoped to its current collection. For the initial core without accepted hierarchy tables, the collection is Workspace; a later parent field will extend the scope to the parent collection.

Sparse integer ranks are selected over contiguous integers because inserting or moving a Scene can often update only the moved row. They are preferred over decimals or lexical/fractional keys because they require no external algorithm, have clear comparison/export semantics, and avoid precision or key-growth concerns.

The database enforces a valid range and, where practical, uniqueness within the ordering scope. Reorder services handle temporary collisions using a transaction, staged values, or deferrable uniqueness where supported. Exact initial gap, rebalance threshold, maximum value, signedness, and collision algorithm remain implementation decisions.

When no gap remains, a bounded rebalance rewrites ordering values in the affected collection without changing Scene IDs, revision content, current pointers, or revision numbers. Reorder advances Scene concurrency versions according to the accepted policy and records an operation when needed.

Contiguous integers are simpler but cause broad renumbering. Decimal ranks introduce precision and canonical export questions. Lexical/fractional keys add algorithm and package complexity. Deferring ordering would tempt timestamps or UUID order to become accidental authority, so an explicit initial column is selected now.

## Workspace Consistency Constraints

The schema must prevent cross-Workspace combinations structurally where PostgreSQL permits.

Required patterns include:

- Workspace has unique primary UUID identity;
- Scene has a direct Workspace foreign key and a unique composite candidate key including Workspace and Scene ID where needed for composite references;
- Scene Revision has direct Workspace and Scene fields;
- a composite foreign key from Revision `(Workspace, Scene)` references Scene `(Workspace, ID)`;
- Scene Revision exposes a composite candidate key sufficient for Scene current-pointer and lineage references to validate Workspace and Scene;
- Scene current revision references a Revision with the same Workspace and Scene;
- predecessor, base, and restoration source reference revisions within the same Workspace and Scene;
- Mutation Operation carries Workspace, and Revision operation references an operation from that Workspace;
- Workspace Grant directly references valid Account and Workspace; and
- cross-Workspace combinations fail at insertion/update rather than relying solely on later audits.

PostgreSQL foreign keys require referenced columns to be primary or unique. The physical schema may add composite uniqueness that is logically redundant with UUID primary identity solely to support enforceable same-Workspace foreign keys. This is accepted controlled index cost.

Django's standard foreign-key abstraction may not express every multi-column relationship as a first-class relation. Models may retain ordinary single-column navigation for ORM ergonomics while reviewed explicit migration operations add composite database constraints. Service validation remains mandatory.

Check constraints cannot safely enforce arbitrary cross-row relationships in PostgreSQL. Cross-row consistency uses foreign keys/unique constraints, not unsupported cross-row checks. Exact deferrability and validation staging remain physical migration details.

## Lineage and Restoration Constraints

Predecessor, base, and restoration-source references point to Scene Revisions within the same Scene and Workspace.

Logical rules are:

- the initial revision has no predecessor and no base;
- an ordinary save's predecessor is the previously current revision;
- an ordinary save's base normally equals predecessor;
- a restoration revision additionally identifies the older restoration-source revision;
- lineage cannot point to the revision itself;
- lineage cannot cross Scene or Workspace;
- current pointer is not lineage and may advance independently only through a new valid revision; and
- cycles or unreachable histories are integrity failures.

Composite foreign keys enforce same-Scene/Workspace reference targets. Row-local checks may reject self-reference. General cycle detection and predecessor-chain semantics require Django service validation and integrity verification because PostgreSQL check constraints cannot safely inspect arbitrary related rows.

Lineage foreign keys use protective deletion behavior. Restoration creates a new revision and operation record; it does not mutate the source or predecessor.

Exact predecessor/base nullability for imports/migrations, branch handling, cycle-check implementation, and constraint deferrability remain later design details consistent with ADR-0004.

## Immutability Enforcement

Ordinary Scene Revision immutability is enforced first through a deliberately narrow write surface:

- only the invariant-preserving creation/save/restore service inserts revisions;
- no ordinary update or delete application service exists;
- model/admin exposure does not permit revision editing;
- application database privileges restrict direct update/delete where practical;
- protective foreign keys prevent ordinary dependency removal;
- integrity metadata and archive/backup verification detect changes; and
- later tests prove ordinary paths cannot mutate history.

Database administrators retain technical capability. Privilege is not domain authorization, and emergency repair must preserve evidence, rotate access where relevant, reconcile invariants, and receive explicit owner review.

Triggers are not required initially. A trigger that blocks all updates/deletes could strengthen immutability but can obstruct Django migrations, isolated restoration, controlled repair, and schema evolution. If later selected, it must be transparent, narrowly structural, documented with bypass authority, and tested across backup/restoration and migrations. It must not infer Canon, provenance, content normalization, or author intent.

Database privileges plus service-level immutability are selected over application-only convention because they provide defense in depth without embedding creative policy in triggers.

## Deletion and Foreign-Key Behavior

Authoritative and security-relevant relationships use protective deletion behavior by default.

- Account deletion is protected while grants or attributable operations require it; account disablement is ordinary.
- Workspace deletion is protected while any Grant, Scene, Revision, or Operation exists.
- Workspace Grant is revoked through state, not casually cascade-deleted.
- Scene ordinary deletion changes lifecycle to trashed.
- Scene physical deletion is protected while revisions exist.
- Scene Revision deletion is protected by current-pointer, lineage, operation, archive, and history requirements.
- Mutation Operation deletion is protected while revisions reference it.
- actor references may use carefully chosen nullification only if account erasure policy later requires it and attribution remains explainable.

Physical cascades may be appropriate later for purely derived/cache rows because they are rebuildable. They are not appropriate for authoritative revision history or ordinary trash.

Purge requires a later decision covering revision history, links, provenance, exports, backups, legal/retention duties, integrity evidence, and recovery. This ADR does not define purge SQL or retention.

## Django Migration Strategy

Django migrations are the primary, version-controlled schema mechanism. Model changes generate or inform migration operations, but every migration and resulting SQL is reviewed before application.

Use standard Django operations for tables, native UUID fields, ordinary foreign keys, checks, uniqueness, and indexes where they accurately express the invariant. Use reviewed explicit database migration operations for composite foreign keys, constraint deferrability, staged validation, or privileges that supported Django APIs cannot express cleanly.

Explicit database operations must keep Django's migration state aligned with actual PostgreSQL state. They must include forward behavior, safe reversal or a documented irreversible boundary, dependency order, expected locks, failure behavior, and backup/restoration implications.

Handwritten SQL files and ad hoc production SQL are not the primary migration mechanism. Operational repair SQL, if ever required, is separate, protected, reviewed, attributable, backed up, and reconciled; it does not masquerade as a migration.

One giant initial migration is rejected because it obscures dependency boundaries and makes circular relations harder to reason about. Excessive micro-migrations are also unnecessary. A small ordered foundational sequence is selected.

No migrations are created by this ADR.

## Initial Migration Sequence

The recommended sequence is:

1. **Account foundation.** Establish the custom Account model and authentication swappable dependency boundary before any dependent application migration.
2. **Workspace foundation.** Create Workspace with UUID identity and minimal operational fields.
3. **Workspace Grant.** Create direct Account/Workspace relationships, grant state, protective deletion, and initial uniqueness that does not preclude later evolution.
4. **Mutation Operation.** Create the narrow Workspace-scoped provenance-operation record with actor/source boundary.
5. **Scene base.** Create Scene with UUID, Workspace, title, lifecycle, sparse order, version, timestamps, and a nullable current-revision placeholder or add that pointer later; no body content.
6. **Scene Revision.** Create immutable snapshot fields, Workspace/Scene relationships, revision number, content/normalization versions, operation/source/actor, timestamps, and initially staged lineage references.
7. **Current-revision relationship.** Add Scene-to-Revision pointer after both tables exist and establish protective behavior.
8. **Workspace and lineage integrity.** Add composite candidate keys/foreign keys for Revision-to-Scene, Scene-to-current-Revision, operation scope, and lineage same-Scene/Workspace relationships.
9. **Row-local constraints.** Add lifecycle values, version bounds, revision-number bounds/uniqueness, ordering range/scope, content-format/normalization values, and self-reference checks.
10. **Validation and privilege stage.** Validate staged constraints as supported, establish ordinary revision write privileges where practical, and add integrity-check expectations.
11. **Bootstrap boundary.** Run a separate protected owner/Workspace/Grant bootstrap workflow after migrations; do not embed owner data or credentials in schema migrations.

These may be combined into a few coherent migration files when Django dependency ordering remains clear. The order is a dependency design, not a mandated migration-file count.

No production data exists, so constraints may be established immediately rather than carried as long-lived unvalidated compatibility scaffolding. Staged addition remains useful to break circular relationships and keep reversibility clear.

## Bootstrap Boundary

Schema migrations create structure only. They do not create the real owner Account, password, WebAuthn credential, recovery code, Workspace display data, or owner-specific Grant.

Initial enrollment occurs after migrations through ADR-0005's protected bootstrap workflow, likely a deployment-controlled management command or equivalent one-time operation. The exact mechanism remains undecided.

Bootstrap creates Account, initial Workspace, and owner Grant in an explicit transaction where feasible, records bounded security/provenance evidence, and invalidates the enrollment capability after success. It never places plaintext passwords, secrets, tokens, recovery material, or private content in migration files, fixtures, source control, or logs.

Data migrations may later create non-secret system vocabulary where unavoidable, but lifecycle/source categories should prefer schema-level constrained values or application constants unless relational reference tables are separately justified.

## Transaction Boundaries

### Scene creation

One transaction creates Mutation Operation, Scene, initial empty Scene Revision, current pointer, and initial version. Failure leaves none of them committed.

### First revision creation

The initial empty revision is part of Scene creation, so no ordinary Scene exists while awaiting a first content revision. The first author content save creates the next revision through the ordinary save transaction.

### Ordinary save

The service authenticates, authorizes, Workspace-scopes, validates CSRF/content/normalization, checks idempotency, and conditionally matches current version/revision. It allocates the next revision number, inserts operation and revision, advances pointer/version, and commits atomically.

### Stale save

A stale conditional update affects zero current Scene rows. The transaction rolls back inserted operation/revision work, leaving no authoritative orphan. Submitted content follows conflict-draft rules outside revision history.

### Restore revision

Restore validates the selected source, creates a new operation/revision with restoration lineage, and advances current pointer/version through the same transaction. It never updates an old revision.

### Lifecycle transitions

Archive, trash, and restore-current-lifecycle operations validate allowed transitions, update status/timestamps, advance Scene version, and create operation/provenance evidence where required. They do not rewrite body revisions.

### Reordering

Reorder updates sparse order values in a transaction, resolves collisions/rebalance within the scoped collection, advances affected Scene versions under policy, and does not change identity or revision content.

### Grant creation and revocation

Grant mutations lock or otherwise protect the relevant Account/Workspace/grant state, enforce Version 1 active-owner uniqueness, create security events separately, and fail closed without deleting Workspace content.

### Migration and bootstrap

Migrations establish schema deterministically. Bootstrap creates deployment-specific owner state separately. Neither uses browser sessions or embeds secrets.

Exact SQL locking syntax, isolation level usage, retry policy, and transaction nesting remain implementation details, but the ADR-0004 atomic-save invariant is mandatory.

## Backup, Export, and Restoration Implications

Every authoritative core table—Account identity boundary as safely required, Workspace, Grant, Scene, Scene Revision, and Mutation Operation—must be considered explicitly in backup scope. Authentication secrets and sessions follow ADR-0005 and are not blindly activated by restoration.

Structured archive export preserves:

- Workspace, Scene, Revision, Grant/Account references as appropriate, and Operation UUIDs;
- Scene current pointer and integer version;
- exact revision content, content-format version, and normalization version;
- revision number and lineage/base/restoration relationships;
- lifecycle status and relevant timestamps;
- sparse ordering value and scope;
- authoring source and bounded provenance references; and
- manifest, schema/archive version, counts, and integrity metadata.

An export is not a database backup. Author-facing exports may omit authentication/security state and operational details while a backup preserves what isolated recovery requires.

Same-archive restoration preserves UUIDs exactly. It loads data in dependency order, temporarily accommodates circular current pointers through staged insertion, validates composite Workspace/Scene relationships, and activates only after every pointer, lineage chain, lifecycle value, order, operation, and content value is verified.

Import into a different Workspace is not restoration and receives new Strange Novelty identity mappings under ADR-0004. Old Story Engine integer IDs remain source provenance only.

Migration sequencing must permit isolated restoration without disabling invariants indefinitely. Derived search, counts, previews, rendering caches, and backlinks can be rebuilt and need not constrain the initial core schema.

Rollback must distinguish application-schema rollback from data restoration. A migration reversal is not a substitute for backup recovery, and destructive schema changes require verified recovery evidence before execution.

## Django ORM Boundary

Django models will expose native UUID primary keys, explicit ordinary foreign keys for common navigation, constrained choices/validators, and transactional service APIs. Abstract bases may share behavior without creating a universal parent table.

The ORM is not the only integrity layer. Model validation does not run on every bulk/query path and cannot protect direct SQL or all concurrent writes. PostgreSQL constraints remain authoritative for structural facts.

Composite same-Workspace foreign keys may require database constraints beyond Django's conventional single-column relation representation. ORM fields can remain individually navigable while explicit migrations reinforce the composite invariant.

Generic foreign keys/content types are not selected as the default for actor, provenance source, lineage, or current pointer. Typed future subsystem relations are preferred.

Django admin, if later enabled, must not expose revision editing, bypass Workspace scoping, or equate staff status with creative approval. Bulk update/delete paths require explicit restriction.

Exact model names, field names, managers, validation APIs, admin registrations, migration operations, and supported Django version remain undecided.

## PostgreSQL Boundary

PostgreSQL provides native UUID storage, primary/unique keys, foreign keys, row-local check constraints, transactions, text storage, privileges, and later selected indexes.

PostgreSQL limitations shape the design:

- cross-row check constraints are not a safe mechanism for parent/Workspace or cycle rules;
- referenced composite columns must be protected by primary/unique constraints;
- general lineage cycle detection remains an application/integrity-check concern;
- deferrable constraints may solve some circular/reorder sequencing but require explicit review;
- generated columns may support derived values but cannot become a second authoritative source; and
- triggers can enforce structure but complicate migrations/restoration and are not selected initially.

Database constraints do not authenticate actors, establish Workspace grants, interpret Canon, approve imports/AI, or authorize purge. Django services do.

PostgreSQL row-level security remains optional future defense in depth. It is not required because its connection context, job, migration, bootstrap, backup, restoration, and administrator behavior need a separate deployment-aware decision.

Exact PostgreSQL version, index methods, storage parameters, collation, constraint names, privileges, deferrability, and backup tooling remain later implementation/operational choices.

## Rationale

Creating the custom Account model before the first migration avoids a notoriously difficult later authentication-model replacement while preserving a clean separation between authentication and Workspace creative state.

Native UUID primary keys make stable application identity the sole core identity, simplify foreign keys and archives, and avoid exposing database-local sequences. The narrow initial workload does not justify dual keys.

An explicit empty initial revision gives every committed Scene one uniform content/current-token model. Physical pointer nullability handles circular creation and restoration mechanics without making null an ordinary domain state.

Direct Workspace columns plus composite constraints prevent cross-Workspace corruption at the database boundary. Application services still enforce current authorization and creative meaning.

Sparse integer ordering is understandable, exportable, package-free, and less rewrite-heavy than contiguous positions. A narrow Mutation Operation record gives revisions stable source attribution without committing to event sourcing or every supporting subsystem.

Multiple ordered Django migrations make circular dependencies and reviewed explicit constraints visible. Backup/archive/restoration requirements shape the schema before any production data exists.

## Decision Criteria

Physical choices are evaluated against:

1. fidelity to ADR-0001 through ADR-0007;
2. clear stable identity and referential integrity;
3. cross-Workspace isolation and constraint coverage;
4. exact immutable revision history and current selection;
5. safe Django custom-user and migration dependencies;
6. atomic creation/save/restore behavior;
7. explicit lifecycle, ordering, and provenance semantics;
8. protective deletion and future purge safety;
9. Django ORM maintainability without weakening PostgreSQL invariants;
10. structured archive, backup, isolated restoration, and migration portability;
11. minimal package and operational complexity for one owner;
12. ability to add later domain/supporting tables without generic polymorphism; and
13. separation of durable correctness from later performance tuning.

## Alternatives Considered

### UUID primary keys on all core authoritative tables

Selected for the narrow core. One stable identity simplifies relationships, export, restoration, and debugging while avoiding sequence exposure.

### Integer primary keys plus unique UUID application IDs

Not selected initially. This can improve narrow index locality/storage in some workloads, but creates two identities, duplicate uniqueness, and ambiguous foreign-key conventions without evidence of need.

### Mixed key strategies by record type

Rejected for the core because inconsistency increases ORM, migration, export, and relationship complexity. Later high-volume supporting tables may justify a separate strategy through evidence.

### Native PostgreSQL UUID columns

Selected. They provide validation, compact binary semantics, native operators, and direct Django support.

### Character columns containing UUID strings

Rejected because they waste space, weaken type enforcement, and complicate canonical comparison/indexing.

### UUIDv7 generation

Preferred under ADR-0004 when supported reliably. It improves likely locality but never defines order/current state.

### UUIDv4 fallback

Accepted when UUIDv7 support is not sufficiently mature or operationally clear. It preserves the schema and contracts.

### Django built-in user table

Not selected as the direct project Account boundary because changing later after dependent migrations is difficult and future authentication requirements may need project ownership of the model boundary.

### Custom Django user model before first migration

Selected. The model can remain minimal while preserving future evolution and stable UUID identity.

### Project-owned profile linked to Django user

Useful for non-authentication profile/domain fields but does not solve later user-model replacement or UUID Account identity cleanly. Not selected as the primary Account boundary.

### Direct Account foreign keys from Workspace Grant

Selected. It is typed, constrainable, and clear. Authentication does not substitute for the grant.

### Generic actor references

Rejected as default because they weaken foreign-key integrity and mix humans/services. Optional service attribution is bounded separately.

### Current-revision foreign key on Scene

Selected as the sole current selector.

### Infer current revision from newest timestamp or revision number

Rejected because timestamps/order are not transactional current authority and concurrent/import/restoration ordering may differ.

### Nullable pointer sequencing

Selected physically for circular construction/migration/restoration, with a stricter ordinary service invariant requiring a committed pointer.

### Deferred constraints

Potentially useful for circular pointer creation and reorder uniqueness. They require targeted evidence and explicit migration operations; not every constraint should be deferred.

### Application-only validation

Rejected for same-Workspace and structural invariants because alternate code paths, concurrency, and direct operations can bypass it.

### Composite structures including Workspace

Selected where feasible. They add indexes/modeling complexity but enforce isolation at the database boundary.

### Surrogate FKs plus duplicate Workspace and checks

Ordinary single-column FKs plus application validation are retained for ORM navigation, but cross-row checks cannot prove same Workspace. Composite FKs are required where the invariant is critical.

### Database triggers for immutability

Deferred. They can block unauthorized updates but complicate migration/restoration and privileged repair. Service surface plus privileges is selected first.

### Database privileges plus service immutability

Selected as defense in depth. It remains explicit and operationally manageable without creative policy in triggers.

### Physical deletion cascades

Rejected for authoritative records because ordinary deletion must be reversible and history preserved.

### Protective deletion behavior

Selected for core authority/history relations.

### Constrained lifecycle status

Selected. It prevents contradictory booleans and supports explicit transitions.

### Separate archive and trash tables

Not selected initially. They add synchronization/joins without a demonstrated need beyond constrained current state plus provenance.

### Contiguous integer ordering

Simple but causes broad renumbering on insertion/move. Not preferred.

### Sparse integer ordering

Selected. It is simple, package-free, exact, and usually limits updates.

### Decimal ordering

Possible but introduces precision/scale, canonical serialization, and rebalance questions without clear benefit over sparse integers.

### Fractional or lexical ordering keys

Powerful for collaborative/local-first ordering, but algorithm and key-growth complexity exceed Version 1 needs.

### Defer ordering

Rejected because UUID/time/row order would become an accidental temporary contract and leak into archives.

### Provenance fields on Scene Revision

Selected for common immutable interpretation, but not sufficient alone for richer multi-source operations.

### Common Mutation Operation table

Selected narrowly. It supports stable shared attribution/idempotency linkage without event sourcing.

### Typed source tables

Deferred to import, AI, restoration, migration, and repair ADRs. They will reference Mutation Operation where appropriate.

### JSON provenance payloads

Allowed only as bounded versioned supplementary metadata. Rejected as the sole relationship model.

### One large initial migration

Rejected because it hides circular dependencies, constraint staging, and review boundaries.

### Multiple ordered foundational migrations

Selected. They make dependency and rollback boundaries visible without excessive fragmentation.

### Django-generated migrations with reviewed SQL

Selected as the primary mechanism, supplemented by explicit database operations for unsupported constraints.

### Handwritten SQL as primary schema mechanism

Rejected because it weakens Django migration state, portability, dependency tracking, and team understanding. Reviewed SQL remains a targeted tool.

### Initial empty revision

Selected for uniform current-content/token behavior, at the cost of an extra row/transaction work during Scene creation.

### Null pointer until first save

Rejected as ordinary state because it makes no-content and empty-content distinct in every read/export/restore path and complicates concurrency tokens.

## Comparative Assessment

### Key strategy comparison

| Strategy | Identity clarity | Index/storage cost | Export/restore | Decision |
| --- | --- | --- | --- | --- |
| UUID physical PK | One identity | Larger than integer | Direct | Selected core |
| Integer PK + UUID | Two identities | Extra indexes | Mapping discipline | Not selected |
| Mixed keys | Variable | Optimizable | Complex | Rejected core |
| Native UUID | Strong typing | Efficient native | Standard | Selected |
| UUID strings | Weak typing | Larger | Canonicalization risk | Rejected |

### Account boundary comparison

| Approach | Future flexibility | Initial complexity | Migration risk | Decision |
| --- | --- | --- | --- | --- |
| Built-in user directly | Lower | Lowest | High if replaced | Not selected |
| Custom Account initially | High | Moderate | Lowest before data | Selected |
| Built-in user + profile | Moderate | Moderate | User boundary remains fixed | Not primary |

### Empty-Scene comparison

| Model | Read/editor uniformity | Creation complexity | Pointer integrity | Decision |
| --- | --- | --- | --- | --- |
| Initial empty revision | Strong | Atomic multi-row | Non-null after commit | Selected |
| Null until first save | Two ordinary states | Simple | Null ambiguous | Rejected ordinary model |
| Deferred non-null FK insertion | Strong | Constraint complexity | Strong | Possible later tightening |

### Ordering comparison

| Representation | Insert cost | Precision/key growth | Export clarity | Decision |
| --- | --- | --- | --- | --- |
| Contiguous integer | Broad rewrites | None | Strong | Not preferred |
| Sparse integer | Usually local | Periodic rebalance | Strong | Selected |
| Decimal rank | Usually local | Precision concerns | Moderate | Not selected |
| Lexical/fractional | Local | Key growth/algorithm | Moderate | Deferred |
| No explicit order | Accidental order | N/A | Weak | Rejected |

### Immutability comparison

| Enforcement | Ordinary protection | Migration/restore fit | Complexity | Decision |
| --- | --- | --- | --- | --- |
| Service only | Moderate | Strong | Low | Insufficient alone |
| Service + privileges | Strong | Manageable | Moderate | Selected |
| Blocking triggers | Strongest DB guard | Complicated | High | Deferred |
| Administrator prohibition claim | Unrealistic | N/A | N/A | Rejected |

### Migration comparison

| Strategy | Dependency clarity | Django state | Special constraints | Decision |
| --- | --- | --- | --- | --- |
| One giant migration | Low | Strong | Hard to stage | Rejected |
| Ordered migrations | Strong | Strong | Staged | Selected |
| Generated only, unreviewed | Moderate | Strong | May omit invariants | Rejected |
| Django + reviewed DB operations | Strong | Strong if synchronized | Strong | Selected |
| Handwritten SQL primary | Manual | Weak | Flexible | Rejected |

## Evidence

### Repository evidence

- Product principles require privacy, authorial control, reversibility, portability, backup, and recovery.
- Version 1 scope requires secure sign-in and dependable Scene drafting/revision without premature broad features.
- The architecture documents establish Django mediation, PostgreSQL authority, explicit Workspace ownership, typed records, provenance, rebuildable derived data, and isolated restoration.
- ADR-0001 through ADR-0007 fix the trust, runtime, database, identity, revision, concurrency, authentication, content, and logical-schema boundaries this physical design implements.
- The architecture handoff explicitly recommends physical schema next and requires backup/restoration to influence it before models.
- The old Story Engine audit identifies integer IDs, missing Workspace scope, in-place content, selective snapshots, broad browser authority, and incomplete recovery as patterns not to preserve.

### Official guidance reviewed conceptually

The design is informed conceptually by current official material without binding to an exact version:

- [Django custom user model guidance](https://docs.djangoproject.com/en/stable/topics/auth/customizing/)
- [Django model fields](https://docs.djangoproject.com/en/stable/ref/models/fields/)
- [Django model constraints](https://docs.djangoproject.com/en/stable/ref/models/constraints/)
- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [Django migrations](https://docs.djangoproject.com/en/stable/topics/migrations/)
- [Django migration operations](https://docs.djangoproject.com/en/stable/ref/migration-operations/)
- [Django foreign-key deletion behavior](https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey.on_delete)
- [PostgreSQL UUID type](https://www.postgresql.org/docs/current/datatype-uuid.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL privileges](https://www.postgresql.org/docs/current/ddl-priv.html)
- [PostgreSQL generated columns](https://www.postgresql.org/docs/current/ddl-generated-columns.html)
- [PostgreSQL trigger behavior](https://www.postgresql.org/docs/current/triggers.html)
- [PostgreSQL backup and restore](https://www.postgresql.org/docs/current/backup.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Insecure Direct Object Reference Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)

This guidance supports choosing a custom user before initial migrations, using native typed fields, enforcing relational facts with constraints, understanding cross-row check limitations, reviewing migration SQL, using transactions for multi-row invariants, protecting deletion, and treating database isolation as defense in depth rather than authorization replacement.

### Evidence still required

Before acceptance or implementation:

- select supported Python/Django/PostgreSQL versions and confirm custom Account requirements;
- confirm maintained UUIDv7 support or select UUIDv4 fallback before the first record;
- prototype native UUID primary-key behavior and migration serialization;
- prototype composite same-Workspace foreign keys and Django migration state synchronization;
- test circular Scene/current-revision migration and transactional creation approaches;
- decide exact initial Scene version and constrained serialized vocabulary;
- test Scene-scoped revision-number allocation under concurrent saves;
- measure sparse integer ordering and rebalance behavior with synthetic data;
- define Mutation Operation minimum fields and typed future references;
- test ordinary revision privileges without blocking migration/restoration roles;
- define all protective/nullifying deletion choices in a physical-schema review;
- inspect generated SQL, locks, reversibility, and constraint validation for each foundational migration;
- define structured archive manifests and restoration insertion order before models are finalized;
- test isolated restoration of circular pointers and composite constraints using synthetic archives; and
- document bootstrap, database roles, backup prerequisite, rollback, and emergency repair procedures.

## Consequences

### Positive

- The Account boundary is correct before any dependent migration exists.
- Core records have one stable UUID identity across database, API, archive, and restoration.
- Same-Workspace corruption is rejected by PostgreSQL where feasible.
- Every committed Scene has uniform initial content and current-token semantics.
- Scene body content cannot diverge between aggregate and revision tables.
- Revision display sequence and aggregate concurrency remain distinct.
- Lifecycle and ordering are explicit from the initial schema.
- Provenance has a stable common operation reference without event sourcing.
- Protective deletion preserves immutable history.
- Ordered migrations expose circular dependencies and recovery implications for review.

### Negative

- UUID primary keys and composite uniqueness consume more index space than integer-only keys.
- Repeated Workspace columns and composite foreign keys add schema/ORM complexity.
- Physical current-pointer nullability is weaker than the ordinary non-null domain invariant.
- Initial empty revisions add rows and transactional work for every Scene creation.
- Custom Account setup adds initial design work before authentication policy is complete.
- Sparse integer ordering eventually requires rebalance logic.
- Scene version advances for metadata/reorder changes may create more editor conflicts.
- Mutation Operation adds a table before import/AI/job schemas exist.
- Database privileges for insert-only revisions complicate migration/restoration roles.
- Explicit database migration operations require careful Django state synchronization.

### Neutral or Operational

- Exact names, lengths, indexes, and constraint names remain implementation work.
- Revision numbers are useful display data but not portable identity.
- Current pointer may be physically nullable while ordinary active Scenes require it.
- Row-level security remains available later.
- Triggers remain available if privileges/services prove insufficient.
- Derived indexes and caches remain outside the foundational migrations.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Custom Account is defined too narrowly | Later auth migration difficulty | Keep boundary project-owned/minimal; review supported contract before migration | Some login changes still require migrations |
| UUIDv7 implementation is unreliable | Identity/collision risk | Gate on maintained support; use UUIDv4 fallback | UUIDv4 locality is weaker |
| UUID PK index locality is poor | Write/storage overhead | Prefer v7 when reliable; measure before alternate keys | Small V1 unlikely to expose severe impact |
| Composite constraints are omitted | Cross-Workspace corruption | Prototype early; explicit migrations; service validation; integrity tests | ORM paths remain complex |
| Composite indexes multiply storage | Increased database size/write cost | Limit to required invariants; avoid speculative indexes | Integrity has unavoidable cost |
| Current pointer remains null | Broken editor/export/restoration state | Atomic initial revision, fail-closed services, integrity checks | Privileged/manual writes can violate it |
| Circular FKs block insertion/restoration | Failed creation or restore | Nullable staged pointer, ordered loading, targeted deferral where proven | Migration logic remains delicate |
| Initial empty revision is skipped | Two content-state models | Single creation service and transaction; validation after bootstrap/restore | Direct admin/SQL paths remain risky |
| Revision number races | Duplicate/conflicting display sequence | Allocate inside save transaction; unique Scene constraint | Contention may require locking strategy |
| Scene version semantics cause false conflicts | Editing friction | Document mutation set, test metadata/reorder flows | Conservative invalidation remains intentional |
| Scene version fails to advance | Lost-update risk | One mutation service, checks, tests, prohibit direct writes | Future maintenance paths can regress |
| Sparse order exhausts gaps | Broad reorder/rebalance | Bounded transactional rebalance and tests | Very active lists still rewrite rows |
| Lifecycle timestamps contradict status | Confusing recovery state | Row-local checks where safe, service transition validation | Historical repairs may need exceptions |
| Operation table becomes event-sourcing dump | Complexity/privacy leakage | Narrow typed fields, no manuscript bodies, no replay authority | Future subsystems may pressure generic metadata |
| Protective FKs block legitimate purge | Operational complexity | Later explicit purge plan and dependency preview | Purge remains intentionally difficult |
| Revision privileges block migrations/restores | Failed operations | Separate least-privileged roles and documented controlled authority | Role configuration can drift |
| Immutability relies too much on services | History mutation | Privileges, no update paths, integrity metadata, tests; reconsider trigger later | DB admins retain capability |
| Explicit migration SQL diverges from Django state | Broken future migrations | State/database synchronization, SQL review, migration tests | Framework upgrades may change behavior |
| Rollback is assumed to recover data | Data loss | Separate migration rollback from backup restoration; verify backup first | Irreversible transforms remain risky |
| Old Story Engine IDs shape schema | Portability/integrity compromise | Treat as import provenance only | Import mapping remains future work |

## Security and Privacy Review

- Security-sensitive: Yes; the schema enforces Workspace isolation and protects the complete manuscript revision history.
- Primary references: `docs/architecture/security.md`, `docs/architecture/data-model.md`, ADR-0001 through ADR-0007.
- Additional references: product vision, principles, scope, roadmap, AI context, integrations, the architecture handoff, and old Story Engine audit.

### Authorization and isolation

Direct Workspace columns and composite foreign keys reduce cross-Workspace corruption but do not authenticate or authorize a request. Django resolves the Account and active Grant, scopes queries, checks lifecycle and operation rules, and fails closed.

UUIDs, current pointers, grant IDs, operation IDs, revision numbers, and database rows grant no authority by possession. Unauthorized failures avoid confirming private record existence.

### Manuscript and provenance privacy

Complete manuscript content exists only in Scene Revision among core records. Mutation Operation, Grant, Account, lifecycle, and security records contain no manuscript bodies. Titles and bounded metadata remain private and stay out of routine logs where unnecessary.

Security events remain separate from provenance. Authentication credentials, sessions, MFA material, recovery codes, tokens, prompts, and provider responses do not enter core provenance.

### Administrative capability

Database ownership, migration roles, restoration roles, staff/superuser status, and emergency SQL capability are not ordinary authorial permission. They use protected attributable access and cannot silently establish Canon or owner approval.

### Required verification

Before implementation acceptance, synthetic tests must cover:

- Account swappable dependency and UUID identity before dependent migrations;
- grant uniqueness/revocation without Workspace deletion;
- native UUID validation, duplicate rejection, serialization, export, and restoration;
- altered/cross-Workspace Scene, Revision, Operation, current-pointer, and lineage references;
- atomic Scene plus empty initial revision creation and full rollback on every failure point;
- unexpected null current pointers failing closed;
- ordinary save, stale save, idempotent retry, and no orphan revision;
- revision-number concurrency and uniqueness;
- version advancement for content, lifecycle, title/context, reorder, restore, and administrative mutation;
- lifecycle constraints and protective deletion;
- sparse ordering insertion, collision, move, rebalance, export, and restoration;
- rejection of ordinary revision update/delete paths under application privileges;
- migration/restoration paths with controlled elevated privileges;
- generated and explicit migration SQL, state synchronization, reverse operations, and locks;
- bootstrap without secrets or owner data in migrations;
- structured archive completeness and exact isolated restoration; and
- absence of manuscript bodies and credentials from provenance, logs, errors, metrics, and security events.

### Residual risk

A compromised Django process or privileged PostgreSQL operator can access or corrupt private data. Composite constraints cannot express authorization, lineage cycles, or all transition semantics. Physical nullability permits invalid states through privileged/manual paths. Backups may retain trashed or later purged content until retention expires.

## Product and Architecture Alignment

### Product alignment

The schema direction protects authorial control, private ownership, stable identity, exact revision history, reversibility, provenance, export, backup, and recovery while keeping Version 1 narrow.

### Scope alignment

It implements only the foundational Account/Workspace/grant and Scene drafting schema boundaries. It does not prebuild Characters, Locations, full hierarchy, links, teams, public sharing, rich text, broad AI, or integrations.

### ADR alignment

- ADR-0001: all browser and service access remains server-mediated.
- ADR-0002: Django models/migrations will represent a modular-monolith boundary later.
- ADR-0003: PostgreSQL, transactions, constraints, migration review, and recovery verification are preserved.
- ADR-0004: UUID identity, immutable snapshots, current pointer/version, atomic saves, lineage, idempotency, and restore-as-new-revision are preserved.
- ADR-0005: custom Account remains distinct from Grant/Workspace; staff and security records do not imply creative authority.
- ADR-0006: Scene Revision alone stores authoritative normalized UTF-8 plain text and representation versions.
- ADR-0007: explicit relational core, direct Workspace scope, lifecycle, ordering, provenance, and supporting-record separation receive a physical shape.

### Architecture alignment

The design follows explicit Workspace ownership, typed relationships, rebuildable derived data, narrow AI/provider authority, protected exports/backups, and isolated restoration.

### Normative-document impact

If accepted, the data-model, security, and migration/recovery documentation should be reconciled with the chosen custom Account, UUID primary keys, initial empty revision, sparse order, Mutation Operation, composite constraints, and migration sequence. The ADR index should then be updated. No other document is changed by this Proposed ADR.

## Migration and Portability

Native UUID primary keys, explicit Workspace relationships, normalized text, format versions, revision numbers, lineage, lifecycle, order, and operation references are portable application semantics even if another relational engine represents their physical types differently.

Initial migrations establish the full foundation before production data exists. Later migrations must preserve every stable ID, Scene/Revision relationship, current pointer/version, exact content value, format/normalization version, lineage, lifecycle, order, operation, and authoring source.

Migration rollback is safe only when the reverse operation preserves data and invariants. Otherwise the migration must declare its irreversible boundary and require verified backup/restoration rather than pretending schema reversal is recovery.

Structured archive format records schema/representation versions independently of Django migration names. Same-archive restoration preserves IDs. Legacy import creates new IDs/mappings and never uses old integer IDs as core keys.

PostgreSQL-specific composite constraints may require an equivalent enforcement design during future database migration. Their semantic invariant—no cross-Workspace or cross-Scene reference—remains portable even if syntax changes.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Select supported Python, Django, and PostgreSQL versions before generating schema artifacts.
- [ ] Review the minimal custom Account contract and login-identifier deferral.
- [ ] Confirm reliable UUIDv7 support or select UUIDv4 fallback before first persistence.
- [ ] Define exact initial Scene version and serialized constrained values.
- [ ] Define exact Account, Workspace, Grant, Scene, Revision, and Operation fields without expanding scope.
- [ ] Prototype Django/PostgreSQL composite Workspace and lineage constraints using synthetic schema work only after implementation authorization.
- [ ] Confirm current-pointer nullable construction and initial-empty-revision transaction.
- [ ] Define revision-number allocation and concurrency behavior.
- [ ] Define sparse ordering type range, gap policy, uniqueness, collision, and rebalance.
- [ ] Define lifecycle transition timestamps and row-local checks.
- [ ] Define Mutation Operation fields and bounded metadata/version rules.
- [ ] Define database roles/privileges for ordinary revision insert-only behavior, migrations, restoration, and repair.
- [ ] Define every protective/nullifying foreign-key deletion choice.
- [ ] Map the recommended dependency sequence to reviewed Django migrations after explicit implementation authorization.
- [ ] Inspect migration SQL, locks, reversibility, state synchronization, and staged validation.
- [ ] Draft the structured archive, backup, and restoration ADR before finalizing model implementation.
- [ ] Define protected initial owner/Workspace/Grant bootstrap outside migrations.
- [ ] Define integrity-verification queries for null pointers, Workspace mismatch, lineage, cycles, revision numbers, and orders.
- [ ] Add later unit, integration, migration, concurrency, authorization, export, backup, and restoration tests using synthetic data.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes Django initialization, models, migrations, SQL, database objects, fixtures, commands, forms, views, APIs, serializers, templates, JavaScript, CSS, tests, packages, MFA, sessions, recovery, jobs, search, AI, import, export, backup, restoration implementation, production-data access, deployment, modification of the old Story Engine, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No Django project, model, migration, SQL file, database object, fixture, command, form, view, API, serializer, template, JavaScript, CSS, test, package, authentication schema, job, search index, AI integration, import, export, backup, or restoration implementation is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
