# ADR-0007: Core Domain Schema and Workspace-Scoped Record Model

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 logical domain schema and Workspace-scoped record model, while exact Django models, migrations, SQL, table and field names, field lengths, indexes, constraint names, UUID key layout, empty-Scene semantics, version-advance rules, lifecycle vocabulary, ordering algorithm, provenance representation, retention and purge policy, row-level security, package versions, and deployment details remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; domain-modeling, Django, PostgreSQL, authorization, privacy, revision, lifecycle, provenance, export, backup, restoration, and migration perspectives

## Context

Strange Novelty needs a first authoritative relational model that supports a private writing workflow without either collapsing every future creative concept into one generic record or prematurely implementing the entire long-term domain.

Version 1 assumes one locally managed human owner account and one initial private Workspace. It has no teams, invitations, public users, sharing links, or general role marketplace. The architecture must nevertheless permit additional Workspaces later without rewriting global ownership assumptions.

Scene drafting and revision history are the first authoritative creative workflow. Characters, Locations, Objects, Research Notes, Story Arcs, Claims, contextual Canon statements, tags, links, comments, attachments, imports, and AI suggestions may be added later. This ADR identifies their boundaries where necessary but does not design their complete schemas.

ADR-0001 makes the browser untrusted and Django application/query services authoritative for every private read and write. ADR-0002 selects Django. ADR-0003 selects PostgreSQL, explicit Workspace ownership, application-generated stable IDs, relational integrity, transactions, append-oriented history, and rebuildable derived data. ADR-0004 distinguishes Scene from immutable Scene Revision, selects complete snapshots, and defines the version/current-revision concurrency token and atomic save transaction. ADR-0005 separates Account, Workspace authorization, staff/superuser administration, and creative authority. ADR-0006 selects normalized UTF-8 plain text with explicit format and normalization versions as authoritative Scene Revision content.

Consequently, browser drafts, derived renderings, search indexes, AI output, exports, and provider documents are not authoritative domain records merely because they contain content. PostgreSQL constraints and transactions reinforce invariants but do not replace Django authorization, lifecycle validation, provenance rules, concurrency checks, or creative-authority decisions.

The model must distinguish:

- Account identity from Workspace identity;
- authentication from Workspace membership;
- Workspace ownership from Django staff or superuser status;
- domain identity from database row location;
- stable ID from title, slug, path, or ordering;
- aggregate root from child or history record;
- Scene from Scene Revision;
- current state from immutable history;
- lifecycle state from physical deletion;
- archive from trash;
- trash from purge;
- restore from rollback;
- revision lineage from provenance;
- provenance from security audit;
- owner edit from AI suggestion;
- imported content from approved content;
- authoring-source category from Canon authority;
- direct Workspace ownership from indirect parent scoping;
- relational fields from bounded JSON metadata;
- authoritative records from derived indexes and caches;
- conflict drafts from committed revisions;
- idempotency records from creative history;
- timestamps from ordering;
- database constraints from application authorization;
- database-administrator capability from ordinary domain permission; and
- logical schema decisions from physical indexing and performance tuning.

The logical model must be concrete enough to guide a later physical-schema ADR while leaving implementation details open. Exact Python, Django, PostgreSQL, migration, UUID, ordering, provenance, schema, package, and deployment versions remain undecided.

## Decision

If accepted, Version 1 will use the following logical model.

1. Use explicit relational tables for core concepts rather than one generic content table, EAV, broad JSON documents, or event sourcing.
2. Use shared behavior through Django abstract bases or service conventions where useful, while every concrete domain concept retains an explicit table and identity. Do not use Django multi-table inheritance as the domain-identity foundation.
3. Use shared PostgreSQL tables with explicit Workspace foreign keys. Do not create one database or PostgreSQL schema per Workspace.
4. Every private aggregate root carries direct Workspace identity. Important children/history records, including Scene Revision, also carry Workspace identity when it strengthens authorization, integrity, export, restoration, partitioning, or migration.
5. Protect repeated Workspace identity against cross-Workspace inconsistency through composite or equivalent constraints where feasible plus mandatory service validation.
6. Account and Workspace are distinct. An explicit Workspace Membership or Grant relates them, even though Version 1 supports only one owner-level grant.
7. Stable application-generated UUIDs identify authoritative records before persistence. Database sequences, titles, slugs, paths, timestamps, and ordering values are not portable identity or authority.
8. Scene is the mutable aggregate root for Workspace, stable identity, title, organizational/order metadata, lifecycle, current-revision pointer, integer concurrency version, and operational timestamps. It stores no second authoritative body-content value.
9. Scene Revision is an immutable, append-oriented child/history record with its own stable identity, direct Workspace and Scene relationships, complete normalized plain-text content, representation versions, lineage/base relationships, provenance/source attribution, timestamps, and required integrity metadata.
10. Scene current-revision pointer is the only current-content selector and may be null only if the later accepted empty-Scene creation model permits it. It must reference a revision from the same Scene and Workspace.
11. Revision insertion and Scene pointer/version advancement occur in the ADR-0004 transaction. Restore creates a new revision; ordinary editing never updates old revisions in place.
12. Use a constrained lifecycle model rather than contradictory deletion booleans. Active, archived, trashed, and restored behavior is explicit; physical purge is exceptional and defined later.
13. Use explicit ordering values scoped to a parent collection. Ordering never derives from UUID order, timestamps, titles, or row order. The exact ordering algorithm remains later work.
14. Model provenance separately from ordinary timestamps, revision lineage, content state, Canon authority, and security events. Authoring-source categories include owner edit, import, AI-assisted apply, restoration, migration, and emergency administrative repair.
15. Derived search, counts, excerpts, previews, rendering caches, and backlinks are rebuildable and identify their source revision or authoritative record when retained.
16. Browser drafts and rejected conflict drafts are not Scene Revisions. Supporting records for idempotency, jobs, imports, AI suggestions, exports, backups, restoration runs, sessions, authenticators, recovery, and security events remain separate subsystem records.
17. Database constraints enforce identity uniqueness, required relationships, valid Workspace consistency, valid current pointers, and other structural invariants where feasible. Django services remain responsible for authorization and domain meaning.
18. PostgreSQL row-level security is not required by this ADR. Database triggers must not hide creative policy or silently generate authorial state.

## Logical Schema Principles

The core model uses explicit concepts and normalized relational relationships. A table represents one durable kind of record whose identity, lifecycle, authorization, and invariants can be explained without inspecting an arbitrary type discriminator or JSON payload.

Shared concepts—stable ID, Workspace scope, timestamps, lifecycle, provenance references, and concurrency where applicable—may use common Django abstract behavior or shared service conventions. They do not imply one universal base row, polymorphic foreign key, or common lifecycle for every record.

Relational columns and foreign keys represent identity, ownership, hierarchy, current pointers, lineage, membership, lifecycle, ordering scope, and other relationships whose integrity matters. JSON may be used only for bounded, versioned, non-relational metadata after a later decision demonstrates that typed columns or child tables are inappropriate. JSON never becomes the sole representation of Workspace ownership, Scene identity, current revision, lifecycle, authorization, lineage, or complete Scene content.

The logical schema starts with Account reference, Workspace, Workspace Membership/Grant, Scene, Scene Revision, and enough provenance/lifecycle boundaries to preserve accepted invariants. It does not create every entity anticipated by the product vision.

## Account Boundary

Account represents the authenticated local human owner or a framework-compatible reference to that owner. It contains authentication/account metadata, not Workspace creative state.

Account identity:

- is distinct from Workspace identity;
- does not embed a Workspace ID as the account's identity;
- does not imply authorization merely because authentication succeeded;
- does not imply Canon or creative approval;
- may be disabled without deleting any Workspace archive; and
- may later receive grants to additional Workspaces without duplicating the account.

The exact custom-user versus supported Django-user implementation remains undecided. This ADR does not select usernames, email requirements, account fields, authentication packages, or user-table structure.

Django staff/superuser status is an administrative framework capability, not an owner-to-Workspace relationship or creative-authority record. Database administrator capability likewise does not become an ordinary domain permission.

## Workspace Boundary

Workspace is the root authorization, privacy, export, backup, restoration, and future partitioning boundary for private creative data. It has a stable application-generated identity and mutable display metadata.

Workspace identity does not assume that only one Workspace can ever exist. A Workspace ID in a URL, form, job, export, or token does not independently grant access. Services resolve current Account grants and scope all queries using authoritative data.

Workspace may have lifecycle and operational metadata, but exact archival, disablement, transfer, deletion, purge, and ownership-recovery behavior remains a later high-impact policy. A Workspace archive survives Account disablement.

Private aggregate roots belong to exactly one Workspace. Cross-Workspace links, parents, revisions, provenance, imports, AI context, exports, and restoration mixtures fail unless a future accepted operation explicitly defines a safe cross-Workspace boundary.

## Workspace Membership and Authorization Grant

Workspace Membership or Grant explicitly relates an Account to a Workspace. Version 1 may permit exactly one active owner-level grant per Workspace and no invitation/team administration.

The grant exists to prevent global-superuser assumptions and support future Workspaces. Its logical concerns include:

- stable identity where independently referenced;
- Account and Workspace relationships;
- active, revoked, or otherwise constrained grant state;
- creation source and timestamps;
- revocation metadata and bounded provenance/security-event references;
- uniqueness preventing duplicate active owner grants under Version 1 rules; and
- integrity preventing nonexistent or inconsistent Account/Workspace references.

Authentication proves control of an Account. A current grant authorizes consideration for a Workspace. The requested operation still requires record, lifecycle, concurrency, state-transition, and creative-authority checks.

Membership does not mean every action by an administrator or service is approved by the author. Exact future role vocabulary, invitations, teams, transfers, organizations, and multi-owner policy remain outside Version 1.

## Scene Aggregate

Scene is the mutable aggregate root for one drafting unit. It carries:

- a stable Scene ID;
- direct Workspace identity;
- mutable title or label;
- organizational parent reference when the later hierarchy schema introduces it;
- explicit ordering metadata within its parent collection;
- explicit lifecycle state and relevant transition timestamps;
- integer optimistic-concurrency version;
- current Scene Revision pointer, subject to empty-Scene semantics;
- creation and update timestamps as operational metadata; and
- bounded provenance/source references for aggregate-level mutations where needed.

Scene title is a mutable label, not identity. A slug or path, if later added, is a locator only. Creation time, UUIDv7 ordering, row sequence, title sorting, and revision time do not determine author-controlled order.

The Scene row does not store authoritative body text. It must not duplicate current content in a second independently writable column, JSON document, cache, search field, HTML rendering, or editor payload. The current revision pointer selects the authoritative content snapshot.

Scene mutations include title changes, parent moves, reorder, lifecycle changes, current-revision advancement, and other later documented metadata changes. Which mutations advance the integer version must be specified consistently before implementation; content saves always follow ADR-0004.

## Scene Revision

Scene Revision is an immutable complete snapshot of committed Scene content and has its own stable application identity. It carries logically:

- stable revision ID;
- direct Workspace identity;
- parent Scene identity;
- complete normalized UTF-8 plain-text content;
- content-format version;
- normalization version;
- predecessor, base, and restoration-source relationships where required;
- provenance or source-operation relationship;
- authoring-source category;
- creation timestamp;
- optional authenticated actor or bounded service attribution according to privacy rules;
- idempotency/operation reference where needed; and
- integrity metadata required by accepted export, backup, restoration, or verification policy.

Revision lineage identifies content ancestry. It does not by itself state why the mutation occurred, whether content is Canon, whether the author approved a source, or whether the operation was security-sensitive.

A mutable `current` flag on revisions is prohibited as a second source of truth. Scene current-revision pointer is authoritative. A revision number may exist for display, but it is scoped, constrained, and never portable identity.

Revision rows are not updated or deleted through ordinary editing. Restoration creates a new revision containing restored content with explicit lineage and provenance. Migration or emergency repair cannot silently rewrite history.

## Current Revision and Version Boundary

Scene current-revision pointer and integer version jointly represent current mutable Scene state for accepted concurrency behavior.

The pointer:

- may be null only if the later empty-Scene decision permits a never-committed Scene;
- references a revision belonging to the same Scene;
- references a revision belonging to the same Workspace;
- is never inferred from maximum timestamp, UUID order, revision number, insertion order, or a revision flag; and
- advances only through the accepted mutation service and transaction.

The integer version advances monotonically for mutations included in the documented concurrency policy. It is not identity, authorization, a revision count, or a timestamp.

A stale conditional update affects zero current Scene rows and leaves no committed orphan revision. Revision creation and pointer/version advancement remain one transaction. Exact locking, conditional SQL, constraint deferrability, and transaction isolation usage remain physical-schema work.

## Content and Metadata Separation

Authoritative Scene body content lives only in Scene Revision. Scene stores current aggregate metadata. Provenance records why or through what source a change occurred. Security events record bounded authentication or administrative facts. Derived records store rebuildable projections.

This separation prevents:

- mutable Scene text from diverging from current revision content;
- titles or lifecycle state from being embedded inside plain text;
- provenance payloads from copying manuscripts unnecessarily;
- security events from becoming creative history;
- search indexes or HTML caches from becoming recovery sources; and
- editor/browser state from entering authoritative records accidentally.

Metadata can have its own concurrency and revision needs later. This ADR does not require every title or order change to create a Scene Revision because Scene Revision is specifically the committed content snapshot. Aggregate-level audit/provenance must still explain authority-changing mutations where required.

## Lifecycle Model

Version 1 uses a small constrained lifecycle model rather than multiple independent booleans such as `is_deleted`, `is_archived`, `is_hidden`, and `is_active` that can form contradictory states.

The logical vocabulary distinguishes at least:

- active: available for ordinary use;
- archived: intentionally retained but removed from the normal active workflow;
- trashed: reversibly removed and awaiting restore or later purge; and
- restored: a transition back from trash or archive, recorded through state/timestamps/provenance rather than necessarily a permanent separate current status.

Physical purge is not an ordinary lifecycle state. A purged record no longer exists in the ordinary authoritative set, but purge evidence and backup implications require later policy.

Lifecycle transitions are explicit, authenticated, authorized, Workspace-scoped operations. Relevant timestamps and provenance record transitions without making timestamps the state machine. Restoring a trashed Scene changes lifecycle state; it does not rewrite immutable revision content or rewind the current pointer.

Exact status labels, allowed transition graph, Workspace lifecycle, retention, cascade behavior, and purge workflow remain later decisions.

## Ordering Model

Scene ordering is explicit within its Workspace or future parent collection. Ordering values express position only within a defined scope and never become stable identity.

Evaluated algorithms include:

- contiguous integer positions: simple reads but potentially broad rewrites;
- sparse numeric ranks: fewer rewrites with periodic rebalance;
- fractional or lexical ordering keys: flexible insertion with key-growth and concurrency concerns; and
- linked-list predecessor relationships: local updates but harder integrity, querying, and repair.

This ADR selects explicit scoped ordering but leaves the algorithm open until parent collections, concurrency, move behavior, expected scale, and UX are known. Constraints and services must prevent ambiguous cross-parent ordering and treat reordering as an authorized mutation.

UUIDv7 time, creation/update timestamps, titles, revision IDs, and database row order are not ordering authority. Reordering never rewrites Scene Revision content or changes stable Scene identity.

## Provenance Model

Provenance explains why and through what authorized source a domain mutation or revision was produced. It is separate from revision lineage, content state, Canon, timestamps, and security audit.

The logical model supports source categories including:

- owner edit;
- import apply;
- AI-assisted apply;
- restoration;
- migration; and
- emergency administrative repair.

Provenance retains stable references to the target, initiating operation, source records or manifests, actor/service where appropriate, time, transformation/version metadata, and bounded disposition or reason. It does not copy manuscript content where stable references and integrity metadata suffice.

The physical representation may use fields directly on Scene Revision for common immutable attributes plus a separate provenance/operation record for richer source relationships. A single table, typed tables, or append-only operation records remain candidates. Arbitrary unversioned JSON payloads and event sourcing are not selected.

Existence of provenance does not imply truth, quality, Canon, owner approval, or authority to perform another action. Security/login events remain in the security subsystem and never share manuscript-bearing provenance payloads.

## Imported, AI-Assisted, Restored, and Administrative Sources

Owner edit means the authenticated owner explicitly proposed and committed content through the ordinary service. It does not automatically classify that content as Canon.

Imported content retains source identity, transformation warnings, import batch/item references, and Imported state until explicit author review. Placement or editing does not erase imported origin or imply approval.

AI-assisted apply references the AI operation/suggestion and explicit owner action. Provider output itself remains suggestion data. Applying it creates a normal Scene Revision after current authorization, normalization, concurrency, and provenance checks; it does not automatically become Canon.

Restoration of a prior Scene Revision creates a new revision with predecessor/base/current relationships and restoration-source provenance. It is not database rollback and does not mutate the old revision.

Migration records transformation/version evidence and source mappings. Emergency administrative repair is exceptional, attributable, reconciled through application invariants, and never attributed silently as an owner edit or creative approval.

Authoring-source category classifies origin. It does not grant authority or determine content state.

## Conflict Draft Boundary

A rejected stale submission is conflict-recovery content, not a committed Scene Revision. Browser-local drafts likewise remain non-authoritative.

Conflict draft storage, if server-side, belongs to a protected temporary-recovery boundary with direct or resolvable Workspace/Scene/base/current references, bounded retention, authorization, cleanup, and privacy controls. It does not enter the current pointer, revision lineage, search, ordinary exports, AI context, or backups by default.

Deliberately resolving a conflict submits complete proposed content against the newest token through the ordinary mutation service. No automatic branch, merge, or revision is inferred from the existence of a draft.

The exact draft table, browser-storage mechanism, retention, purge behavior, and comparison interface remain outside this logical creative schema.

## Derived Data Boundary

Search vectors, counts, excerpts, previews, rendered HTML, backlinks, comparison artifacts, AI context slices, caches, and materialized projections are derived and rebuildable from authoritative records.

When retained, a derived record identifies:

- its Workspace;
- source record or Scene Revision;
- derivation type and version;
- creation/update status; and
- enough integrity or freshness metadata to detect staleness.

Derived data never becomes the only copy of content, relationship, lifecycle, state, provenance, or order. It may be discarded and rebuilt during deployment, migration, repair, or restoration. On disagreement, authoritative records prevail and verification reports the discrepancy.

Derived queries remain authenticated and Workspace-scoped. Search terms, excerpts, manuscript text, and AI bodies remain outside routine logs and telemetry.

## Supporting Infrastructure Records

The following records are not collapsed into Scene, Scene Revision, or a universal content table:

| Record family | Boundary | Authority rule |
| --- | --- | --- |
| Idempotency operations | Application infrastructure | Deduplicates effects; grants no permission or creative history |
| Background jobs | Application infrastructure | Bounded service authority; revalidates current state |
| Import batches/items | Import subsystem | Staged untrusted input; not approved content automatically |
| AI operations/suggestions | AI subsystem | Suggestion/provenance records; provider output has no authority |
| Derived projections | Query/search/rendering subsystem | Rebuildable; source records prevail |
| Exports | Export subsystem | Private artifacts; not authoritative database state |
| Backups | Recovery subsystem | Broader recovery artifacts; not ordinary content exports |
| Restoration runs | Recovery subsystem | Validated privileged process; does not authenticate a person |
| Sessions/authenticators/recovery | Security subsystem | Authentication state; grants no domain authority independently |
| Security events | Security/audit subsystem | Bounded security facts; no manuscript payloads or Canon meaning |
| Conflict drafts | Temporary recovery subsystem | Sensitive uncommitted content; not revisions |
| Integration grants/jobs | Integration subsystem | Narrow external authority; providers are not source of truth |

Supporting records carry Workspace, actor, source, target, and operation references where required for authorization, attribution, cleanup, export, restoration, or incident response. Those references never grant authority by possession.

Exact physical schemas for these families remain later work unless a foreign-key boundary must be fixed alongside the core schema.

## Workspace Scoping Strategy

Shared PostgreSQL tables use explicit Workspace foreign keys. Separate databases or schemas per Workspace are not selected for Version 1 because they multiply migrations, connections, backup/restoration operations, pooling, observability, and administration without a multi-tenant scale requirement.

Direct Workspace identity appears on every private aggregate root. Important children/history records repeat it when doing so materially strengthens:

- query scoping and omission resistance;
- composite referential integrity;
- cross-Workspace relationship rejection;
- export/backup selection and verification;
- restoration and migration validation;
- future partitioning or archival; and
- incident investigation.

Scene Revision is one such record. It carries Workspace even though Scene also does. Redundancy is controlled, not denormalized authority: the repeated value must match its parent.

Relying only on indirect ownership through parent joins is rejected as the universal pattern because omissions and polymorphic paths become harder to audit. Repeating Workspace on every incidental row is also not automatic; later schemas justify it based on sensitivity and integrity.

Django query services always scope by current authorized Workspace. PostgreSQL row-level security may later add defense in depth but is not required or a substitute for service authorization.

## Foreign-Key and Constraint Strategy

The physical schema must express these logical invariants where PostgreSQL can do so reliably:

- stable IDs are non-null and unique within each authoritative record table;
- required IDs are generated before persistence;
- Workspace Membership references valid Account and Workspace records;
- grant uniqueness/state rules prevent inconsistent duplicate active grants;
- Scene references one valid Workspace;
- Scene Revision references one valid Scene and Workspace;
- Scene Revision Workspace matches Scene Workspace;
- Scene current revision references a revision belonging to that Scene;
- Scene current revision Workspace matches Scene Workspace;
- lineage/base/restoration references remain within the permitted Scene and Workspace;
- cross-Workspace foreign-key combinations fail;
- required format/normalization/source/lifecycle values satisfy constrained vocabularies; and
- display revision numbers or ordering values, if used, are scoped and constrained appropriately.

Composite foreign keys including Workspace are preferred where they make same-Workspace consistency enforceable and maintainable. Surrogate foreign keys plus service validation may be used where Django/PostgreSQL constraints would otherwise be impractical, but they require explicit integrity checks and adversarial tests.

Constraint syntax, names, deferrability, null semantics, generated columns, indexes, partial indexes, and physical uniqueness strategies remain later decisions. A database check cannot query arbitrary other rows, so some immutability and cross-record domain rules require permissions, service boundaries, transactions, or triggers reviewed for narrow structural enforcement.

Database triggers must not contain hidden creative policy, infer Canon, generate author approval, normalize manuscripts invisibly, or create provenance without application context.

## Transaction Boundaries

Revision insertion and Scene current-pointer/version advancement remain one transaction. The service validates authorization, Workspace, lifecycle, content, concurrency, provenance, idempotency, and source category before or inside the transaction as appropriate.

The transaction ensures:

- the submitted version/current-revision token still matches;
- the new revision has the same Workspace and Scene;
- lineage and source references are valid;
- the immutable revision is inserted;
- the current pointer advances to it;
- the integer version advances monotonically; and
- either every authoritative effect commits or none does.

A stale write affects zero current Scene rows and leaves no committed revision from that failed attempt. Owner edit, import apply, AI-assisted apply, restoration, migration, and approved administrative repair use the same invariant-preserving mutation service rather than bespoke direct writes.

Scene reorder, lifecycle transitions, membership revocation, Workspace high-impact operations, export snapshots, and restoration activation each require later documented transaction boundaries. This ADR does not select isolation level, lock mode, retry count, or SQL implementation.

## Immutability Boundary

Scene Revision content, format/normalization metadata, identity, parent relationships, lineage, source/provenance reference, and creation attribution are immutable after commit through ordinary application paths.

Immutability is protected by:

- no ordinary update service for revision content;
- Django model/service conventions that expose insertion and reading only;
- database privileges separating ordinary application mutations where practical;
- structural constraints;
- tests rejecting in-place updates;
- integrity verification in export, backup, migration, and restoration; and
- exceptional repair procedures that preserve evidence and reconcile invariants.

A mutable database row is technically updateable by a sufficiently privileged administrator. That capability is not domain permission. Database-level triggers may reinforce immutability if later justified, but they are not selected here and must allow controlled migration/restoration without hidden policy.

Changing current content always creates a new revision. Correcting erroneous provenance or corruption requires a separately documented repair or migration, not an ordinary edit disguised as maintenance.

## Deletion, Trash, Restore, and Purge

Ordinary delete is reversible: it transitions a Scene to trash rather than physically deleting its row or revisions. Archive removes a Scene from active workflow while retaining it intentionally. Trash indicates reversible removal pending restore or exceptional purge.

Restore from trash changes lifecycle state and placement/order as explicitly determined; it does not alter old revision content. Restoring an older content snapshot is a different operation that creates a new revision under ADR-0004.

Physical purge is exceptional. It requires recent authentication, explicit authorization and intent, dependency review, provenance/security events, export/backup and retention awareness, private-object handling, derived-data cleanup, and a later recovery policy. This ADR does not define retention periods, purge cascades, legal obligations, backup expiration, or user interface.

Database cascade deletion is not an ordinary user-delete mechanism for the Workspace archive. Any later cascades are limited to relationships where lifecycle, history, recovery, and audit requirements explicitly permit them.

Workspace purge and Account deletion have distinct consequences and cannot be inferred from Scene trash behavior. Account disablement preserves the Workspace.

## Django Model Boundary

Django concrete models will eventually represent explicit logical concepts. Shared fields or behavior may use abstract base classes, mixins, managers, query sets, or service conventions without creating a universal polymorphic identity table.

Django multi-table inheritance is not selected for domain identity because it introduces parent rows, implicit joins, coupled lifecycle, confusing polymorphism, and migration complexity without a demonstrated need. Generic foreign keys/content types are not the default relationship model because database foreign keys cannot fully protect endpoint existence, type compatibility, or Workspace consistency.

Application/query services own:

- authentication and Workspace-grant resolution;
- query scoping;
- authorization and creative-authority checks;
- lifecycle transitions;
- concurrency and idempotency;
- provenance/source validation;
- invariant-preserving transactions;
- safe derived-data invalidation; and
- privacy-conscious errors.

Exact custom user model, Django fields, abstract bases, managers, validators, `Meta` constraints, deletion policies, admin registration, serializers, commands, and tests remain undecided.

## PostgreSQL Boundary

PostgreSQL is authoritative for stored relational state and provides transactions, foreign keys, uniqueness, checks, native UUID storage, text-compatible content storage, and later selected indexing.

PostgreSQL reinforces structural integrity but does not decide:

- whether an Account is authorized for a Workspace now;
- whether an owner approved a Canon change;
- whether an AI suggestion should be applied;
- whether an import is trustworthy;
- whether an administrative repair represents author intent; or
- whether a purge is safe under backup and retention policy.

JSON/JSONB may hold bounded versioned non-relational metadata only after later review. Generated columns may support derived values but cannot become a second authoritative content or policy source. Row-level security remains optional future defense in depth.

Exact table layout, column types/lengths, indexes, constraint names, collations, generated columns, partitioning, storage parameters, isolation usage, triggers, and database roles belong to a later physical-schema decision.

## Rationale

Explicit relational concepts fit Strange Novelty's core invariants: stable identity, Workspace authorization, mutable aggregate state, immutable revisions, provenance, lifecycle, ordering, and recovery.

The narrow Account–Workspace grant–Scene–Scene Revision model is sufficient to implement and test the first authoritative writing workflow. It avoids paying now for every future entity while providing conventions future tables can follow.

Direct Workspace ownership makes authorization scope visible and supports export, restoration, migration, and future partitioning. Repeating Workspace on important history rows allows database-enforced consistency and reduces dependence on fragile indirect joins.

Separating Scene current metadata from immutable revision snapshots preserves exact history and prevents dual content authority. Constrained lifecycle, explicit ordering, and separate provenance keep editable labels and operational facts from becoming identity or creative truth.

Typed tables and foreign keys provide stronger integrity and clearer evolution than EAV, generic content tables, generic foreign keys, or broad JSON documents. Django services retain domain meaning while PostgreSQL enforces structural facts.

## Decision Criteria

Strategies are evaluated against:

1. explicit Workspace authorization and cross-Workspace isolation;
2. stable portable identity independent of names and rows;
3. exact immutable Scene revision history and atomic current selection;
4. relational integrity for parent, pointer, lineage, and grant relationships;
5. clear lifecycle, ordering, provenance, and source semantics;
6. separation of creative authority, authentication, security audit, and infrastructure;
7. export, backup, restoration, and migration verification;
8. maintainability and query clarity in Django/PostgreSQL;
9. ability to introduce future Workspaces and domain types safely;
10. avoidance of speculative schema breadth and premature polymorphism;
11. privacy-conscious logging and supporting records;
12. testability of constraints and transactions; and
13. logical stability independent of physical tuning.

## Alternatives Considered

### One generic content-record table

Rejected. A type discriminator plus generic fields would blur lifecycle, required attributes, relationships, constraints, authorization, migrations, and query intent. Shared conventions do not require shared identity storage.

### Separate relational tables for core concepts

Selected. Account reference, Workspace, Grant, Scene, and Scene Revision have distinct identities and invariants that PostgreSQL can enforce clearly.

### Entity-attribute-value storage

Rejected as the main domain model. EAV supports arbitrary fields but weakens types, constraints, referential integrity, query clarity, migrations, validation, export, and restoration.

### JSON-document storage for most records

Rejected as sole authority. It would move Workspace, lifecycle, relationship, pointer, and lineage consistency into application code. Bounded versioned metadata may use JSON later.

### Django multi-table inheritance

Not selected. It adds implicit joins, parent-row lifecycle, polymorphic retrieval, coupled migrations, and unclear aggregate boundaries. Abstract shared behavior is simpler.

### Django abstract base models

Selected as an optional implementation technique for repeated concrete behavior, not a requirement to force identical fields or lifecycle onto every table.

### Generic foreign keys and content types

Rejected as the default relationship mechanism because PostgreSQL cannot enforce ordinary foreign-key existence and same-Workspace rules across arbitrary target tables. Later polymorphic features require explicit review.

### Explicit typed relationship tables

Selected when relationships are introduced. Typed tables or bounded typed endpoints provide clearer validity, constraints, export, and migration than unrestricted polymorphism.

### Event sourcing as primary persistence

Rejected for Version 1. It makes current state projection-dependent and adds event-schema, replay, migration, privacy deletion, debugging, and restoration complexity beyond the accepted snapshot model.

### Current-state tables plus append-only history

Selected. Scene carries current mutable aggregate state while Scene Revision provides immutable complete content history.

### Minimal Scene-only schema

Too narrow if it omits Account, Workspace, explicit grant, provenance, lifecycle, and Workspace integrity. The selected core is minimal but complete enough for authorization and recovery.

### Broad anticipated-entity schema

Rejected. Implementing Characters, Locations, Objects, Claims, Canon, tags, links, comments, attachments, research, and every future concept now would encode untested requirements and delay the first workflow.

### PostgreSQL schema or database per Workspace

Rejected for Version 1. It adds provisioning, migrations, connection management, backup, restoration, and operational complexity without a scale or regulatory requirement.

### Shared tables with explicit Workspace foreign keys

Selected. This is operationally simple, queryable, and compatible with strong constraints and future partitioning.

### Indirect Workspace ownership through parent only

Rejected as the universal approach. It saves repeated columns but makes scope omission, history queries, export, restoration, and cross-parent integrity harder to audit.

### Direct Workspace ownership on roots and important children

Selected with constraints preventing inconsistency. Not every incidental row receives redundant Workspace automatically.

### Soft deletion flag only

Rejected. A boolean cannot distinguish archive, trash, restore, retention, or exceptional purge semantics.

### Explicit lifecycle state plus timestamps

Selected conceptually. A constrained state captures current lifecycle; timestamps/provenance explain transitions. Exact vocabulary remains later work.

### Database-generated integer IDs exposed publicly

Rejected under ADR-0004. Sequences are database-local, enumerable, non-portable, and not authority.

### Application-generated UUID identity

Selected under ADR-0004. UUIDs exist before persistence and survive export, restoration, and migration.

### Workspace foreign key only on aggregate roots

Insufficient for important history and supporting records. It may remain appropriate for tightly bound incidental children where indirect integrity is safe.

### Workspace foreign key repeated on all rows

Overbroad as an absolute rule. Repetition is selected for roots and important child/history/support records where its value outweighs redundancy.

### Composite foreign keys including Workspace

Preferred where feasible for Scene/Revision and other sensitive relationships. They provide database-enforced same-Workspace integrity but complicate Django modeling and indexes.

### Surrogate foreign keys plus service validation

Permitted where composite enforcement is impractical, with explicit integrity checks and adversarial tests. Service validation alone is weaker against bypass paths.

### PostgreSQL row-level security

Deferred as optional defense in depth. It can reduce query-omission risk but complicates connection context, jobs, migrations, backups, restoration, and administration and does not express all creative policy.

### Nullable deleted timestamp

Simple and useful for trash time, but insufficient alone to distinguish active, archived, trashed, restored, and purge semantics.

### Deleted boolean

Rejected as the complete lifecycle model because it has little explanatory power and invites contradictory companion flags.

### Multiple independent lifecycle booleans

Rejected because invalid combinations are easy and transition meaning is unclear.

### Constrained lifecycle status

Selected as current-state representation, accompanied by timestamps and provenance where meaningful.

### Separate archive and trash records

Could preserve transition detail, but adds joins and synchronization with current state. Deferred unless history requirements exceed constrained state plus provenance.

### Event-derived lifecycle state

Rejected for Version 1 because ordinary queries and authorization would depend on replay/projection correctness.

### Physical deletion only

Rejected. It conflicts with reversibility, recovery, provenance, and backup-aware purge.

### Provenance fields on Scene Revision

Selected for common immutable source/actor/operation references. Fields alone may not represent rich import/AI/migration relationships.

### One generic provenance or event table

Possible for common operation records if its schema remains bounded and typed. A universal arbitrary event payload is not selected.

### Typed provenance tables

Potentially strong for source-specific integrity but may multiply schemas prematurely. Later physical design may combine common fields with typed source records.

### Append-only operation records

Promising for shared mutation attribution and idempotency linkage. They support provenance but are not a replacement for domain records or full event sourcing.

### JSON provenance payloads

Allowed only for bounded versioned metadata that does not replace typed target/source/Workspace relationships. Unrestricted payloads are rejected.

### Event sourcing for provenance

Rejected. Provenance can be append-oriented without making all domain state event-derived.

### Timestamps only

Rejected. Timestamps do not explain source, transformation, authorization, Canon, lineage, or actor intent.

## Comparative Assessment

### Core schema comparison

| Strategy | Integrity | Query clarity | Extensibility | V1 complexity | Decision |
| --- | --- | --- | --- | --- | --- |
| Generic content table | Weak/moderate | Low | Superficially high | Moderate | Rejected |
| Explicit relational tables | Strong | Strong | Deliberate | Low/moderate | Selected |
| EAV | Weak | Low | High field flexibility | High | Rejected |
| JSON documents | Application-enforced | Moderate | High | Moderate | Not core authority |
| Multi-table inheritance | Moderate | Moderate/low | Coupled | Moderate | Not selected |
| Abstract concrete models | Strong per table | Strong | Deliberate | Low | Preferred technique |
| Event sourcing | Replay-dependent | Projection-dependent | High | Very high | Rejected V1 |
| Current + append history | Strong | Strong | Strong | Moderate | Selected |

### Workspace-scoping comparison

| Pattern | Isolation visibility | Database enforcement | Operations | Decision |
| --- | --- | --- | --- | --- |
| Root-only Workspace FK | Indirect on children | Moderate | Simple | Insufficient universally |
| Repeat on every row | Highest | Strong if constrained | Redundant | Too absolute |
| Roots + important children | High | Strong where modeled | Balanced | Selected |
| Composite Workspace FKs | High | Strong | Modeling complexity | Preferred where feasible |
| Service validation only | Code-dependent | Weak | Simple schema | Fallback only |
| PostgreSQL RLS | High | Strong row filtering | Operationally complex | Optional future defense |
| Database/schema per Workspace | Physical isolation | Strong | High overhead | Rejected V1 |

### Lifecycle comparison

| Representation | Valid states | Transition clarity | Recovery fit | Decision |
| --- | --- | --- | --- | --- |
| Deleted boolean | Weak | Weak | Weak | Rejected alone |
| Deleted timestamp | Limited | Moderate | Trash-focused | Insufficient alone |
| Independent booleans | Contradictory risk | Weak | Moderate | Rejected |
| Constrained status | Strong | Strong with service rules | Strong | Selected |
| Separate records | Strong history | Strong | Strong | Deferred complexity |
| Event-derived | Strong if stream sound | Strong | Replay-dependent | Rejected V1 |
| Physical deletion | None | Irreversible | Poor | Rejected ordinary path |

### Provenance comparison

| Representation | Typed integrity | Source richness | Complexity | Decision |
| --- | --- | --- | --- | --- |
| Revision fields | Strong/common | Limited | Low | Selected baseline |
| Generic provenance record | Moderate/strong if bounded | Strong | Moderate | Candidate |
| Typed source tables | Strong | Strong | Higher | Candidate as needed |
| Append-only operation record | Strong/common | Strong | Moderate | Candidate |
| JSON payload | Weak alone | Flexible | Low initially | Bounded metadata only |
| Event sourcing | Strong if complete | Strong | Very high | Rejected |
| Timestamps only | Weak | Minimal | Low | Rejected |

## Evidence

### Repository evidence

- Product vision and principles prioritize authorial control, meaningful states, privacy, stable connections, portability, backup, restoration, and a narrow first release.
- Version 1 scope identifies Scene drafting/revision as core and defers broad entity/plugin systems.
- The roadmap requires foundational security, data, export, backup, and restoration decisions before implementation.
- The architecture overview places the browser outside the trusted policy/data boundary.
- The data model requires stable IDs, explicit Workspace ownership, typed concepts, Scene/Revision separation, lifecycle, provenance, rebuildable indexes, staged imports, and non-authoritative AI suggestions.
- The security architecture requires every private query and mutation to be server-authorized and Workspace-scoped, with bounded administrative and service authority.
- ADR-0001 through ADR-0006 establish Django/PostgreSQL boundaries, UUID identity, complete immutable Scene snapshots, atomic concurrency, authentication/grants, and normalized plain-text content.
- The old Story Engine audit identifies integer IDs, missing Workspace scope, in-place updates, selective snapshots, mixed settings/secrets, broad browser authority, and incomplete recovery as patterns not to reuse.

### Official guidance reviewed conceptually

The decision is informed conceptually by current official and security guidance without binding to a specific release:

- [Django models](https://docs.djangoproject.com/en/stable/topics/db/models/)
- [Django model constraints](https://docs.djangoproject.com/en/stable/ref/models/constraints/)
- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [Django deletion behavior](https://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey.on_delete)
- [Django authentication model customization](https://docs.djangoproject.com/en/stable/topics/auth/customizing/)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL transactions and isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL generated columns](https://www.postgresql.org/docs/current/ddl-generated-columns.html)
- [PostgreSQL JSON types](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Insecure Direct Object Reference Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html)

This guidance supports deny-by-default authorization, validation on every request, non-authoritative identifiers, explicit foreign keys and constraints, atomic transactions, careful deletion semantics, bounded JSON use, and defense in depth for tenant/Workspace isolation.

### Evidence still required

Before acceptance or physical-schema implementation:

- confirm the smallest first vertical slice and whether hierarchy parents precede Scene persistence;
- decide the supported Django Account reference/customization path before first migration;
- define grant states and Version 1 owner uniqueness without choosing future role vocabulary;
- decide empty-Scene/current-pointer semantics;
- define exactly which Scene mutations advance the integer version;
- prototype same-Workspace composite constraints in the selected Django/PostgreSQL versions;
- test null current pointers and circular Scene/Revision reference creation order;
- define lineage, base, restoration, operation, and provenance cardinalities;
- define constrained lifecycle vocabulary and allowed transitions;
- test ordering candidates under insert, move, reorder, conflict, and restoration;
- classify which important supporting/child records repeat Workspace identity;
- define immutable-revision enforcement and controlled migration/repair paths;
- define export/archive representation for grants, lifecycle, order, revisions, and provenance;
- test backup/restoration validation of composite Workspace relationships and current pointers;
- define purge dependencies only after retention and backup policy;
- perform adversarial cross-Workspace query, pointer, lineage, provenance, and job tests; and
- create a later physical-schema ADR before models or migrations.

## Consequences

### Positive

- The first authoritative workflow has clear Account, Workspace, grant, Scene, and revision boundaries.
- Workspace scope is visible and enforceable on sensitive records.
- Explicit tables and foreign keys preserve relational integrity and query clarity.
- Scene content has one authoritative location in immutable revisions.
- Current state and history remain understandable without event replay.
- Lifecycle avoids contradictory deletion booleans and preserves reversible trash.
- Explicit order survives title, timestamp, and infrastructure changes.
- Provenance remains distinct from lineage, Canon, and security audit.
- Derived and supporting records cannot silently become creative authority.
- The model leaves room for future Workspaces and entities without implementing them prematurely.

### Negative

- Repeated Workspace foreign keys introduce controlled redundancy.
- Composite same-Workspace constraints may be awkward in Django and require extra uniqueness/index support.
- Explicit tables require migrations when new domain concepts are added.
- Separate current Scene and immutable Revision rows require careful circular pointer/foreign-key creation design.
- Lifecycle, provenance, ordering, and grant concepts add records/fields before the UI exposes their full value.
- Full snapshots consume more storage than patches.
- Application authorization remains mandatory even with strong constraints.
- Optional service-validation fallbacks leave some invariants outside the database.
- Trash and future purge complicate uniqueness, cascades, export, and backup behavior.
- Supporting subsystems still need later schema decisions.

### Neutral or Operational

- One initial Workspace still uses multi-Workspace-safe query patterns.
- UUIDs may be physical primary keys or unique application identities; exact key layout remains physical work.
- Abstract Django bases are an implementation aid, not a domain table.
- PostgreSQL RLS remains available but unrequired.
- JSON remains available for justified bounded metadata.
- Ordering algorithm and provenance physical shape remain open.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Workspace filter omitted | Cross-Workspace disclosure | Direct Workspace fields, scoped services, composite constraints, adversarial tests, optional later RLS | Application regressions remain possible |
| Repeated Workspace values diverge | Corrupt authorization/export scope | Composite FKs where feasible, service validation, integrity checks, restoration verification | Some relationships may resist full DB enforcement |
| Global superuser substitutes for grant | Excess authority/false approval | Explicit grant resolution and creative-authority services | Operators retain technical capability |
| Scene duplicates content | Competing sources of truth | Prohibit authoritative body on Scene; current revision pointer only | Caches may be misused accidentally |
| Current pointer references wrong revision | Wrong content/cross-Workspace exposure | Composite constraints, transaction service, integrity tests | Deferrability/creation ordering is complex |
| Revision updated in place | Lost history/provenance | No update path, privileges, tests, integrity metadata, repair procedure | DB administrators can still mutate physically |
| Stale save leaves orphan revision | Misleading history | One atomic conditional transaction | Exceptional DB failures require verification |
| Lifecycle flags conflict | Hidden/deleted data ambiguity | Constrained status and transition service | Vocabulary may need migration later |
| Trash uniqueness blocks reuse | UX/schema conflict | Define lifecycle-aware uniqueness later; avoid premature names-as-keys | Reuse semantics may remain surprising |
| Purge cascades history unexpectedly | Permanent loss | Exceptional later policy, dependency preview, recent auth, backup awareness | Backups retain purged data until expiry |
| Ordering rewrites too many rows | Contention/latency | Evaluate sparse/fractional approaches with synthetic scale | Any scheme has rebalance/complexity tradeoffs |
| Provenance becomes generic JSON | Weak integrity and opaque history | Typed core references, versioned bounded metadata, validation | New source categories require evolution |
| Provenance implies approval | Incorrect Canon/authority | Separate source, state, and author-approval rules | UI wording can still mislead |
| Generic relationships bypass FKs | Dangling/cross-Workspace links | Prefer explicit typed tables | Future polymorphism remains challenging |
| Supporting record grants authority | Authorization bypass | References are non-authoritative; revalidate actor/Workspace/operation | Implementation confusion remains possible |
| Derived index treated as source | Stale/wrong content | Source IDs, rebuildability, verification, authoritative fallback | Eventual consistency may be visible |
| Broad schema anticipates wrong domain | Migration burden | Implement narrow core and require later ADRs | Some future concepts may need restructuring |
| Schema too narrow for first workflow | Rework before usability | Include authorization, lifecycle, provenance, order boundaries now | Hierarchy/entity dependencies remain open |
| RLS added carelessly | Jobs/admin/restore failures | Separate ADR and deployment-context design | Query-service bugs persist without it |
| Database triggers hide policy | Unreviewable creative mutations | Limit triggers to explicit structural enforcement if later used | Physical schemas can still accumulate complexity |

## Security and Privacy Review

- Security-sensitive: Yes; Workspace scoping and revision integrity protect the complete private archive.
- Primary references: `docs/architecture/security.md`, `docs/architecture/data-model.md`, ADR-0001 through ADR-0006.
- Additional references: product vision, principles, scope, roadmap, AI context, integrations, and the old Story Engine audit.

### Assets and trust boundaries

Protected assets include Account grants, Workspace identity, Scene metadata, immutable manuscript revisions, lifecycle, provenance, conflict drafts, derived indexes, AI suggestions, exports, backups, and restoration state. Browser IDs and payloads, jobs, imports, providers, administrative tools, and restored artifacts cross trust boundaries.

### Authorization

Every private service resolves current Account and grant state, scopes queries by Workspace, and rechecks operation-specific permission. IDs, memberships, foreign keys, sessions, staff flags, current pointers, provenance, idempotency keys, and database access do not independently establish creative authority.

Unauthorized responses avoid confirming private record existence. Cross-Workspace parent, revision, lineage, derived, provenance, import, job, export, backup, and restoration references fail closed.

### Privacy

Manuscript content remains in Scene Revision and protected temporary draft boundaries, not routine logs, security events, URLs, telemetry, or provenance payloads. Supporting records retain stable references and bounded metadata rather than duplicated content where possible.

Database administrators and emergency operators have technical access but no ordinary authorial permission. Access is protected, attributable, exceptional, and reconciled through application invariants.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- Account disablement without Workspace deletion;
- grant activation/revocation and future second-Workspace isolation;
- altered Workspace, Scene, revision, lineage, provenance, and current-pointer IDs;
- composite same-Workspace constraint failures;
- null/valid/invalid current-revision states;
- full save success, stale zero-row update, rollback, retry, and no orphan revision;
- rejection of ordinary revision updates/deletes;
- owner, import, AI, restoration, migration, and administrative sources through one mutation boundary;
- lifecycle transition validity, archive/trash/restore visibility, and reversible delete;
- ordering scope, concurrent reorder, parent move, and no revision rewrite;
- derived-data invalidation, source linkage, rebuild, and Workspace filtering;
- absence of manuscripts from provenance, security events, logs, errors, and metrics;
- export/backup completeness and cross-Workspace rejection;
- isolated restoration of IDs, grants, pointers, lineage, lifecycle, order, provenance, and exact content; and
- database-role and administrative paths that cannot silently attribute creative approval.

### Residual risk

A compromised Django service or privileged database operator can access or corrupt private records. Composite Workspace constraints cannot express every domain rule, and service-layer omissions remain possible. One-owner deployments have limited separation of duties. Backups may retain deleted content, and future entities may expose new cross-Workspace relationship risks.

## Product and Architecture Alignment

### Product alignment

The model protects authorial control, explicit ownership, meaningful content history, provenance, reversibility, privacy, export, and recovery while keeping the first release narrow.

### Scope alignment

It supports the first private Scene drafting/revision workflow without implementing teams, public sharing, arbitrary entity builders, every future story entity, or advanced collaboration.

### ADR alignment

- ADR-0001: Django services mediate all browser and job access.
- ADR-0002: explicit Django models/services will implement the logical boundaries later.
- ADR-0003: PostgreSQL, explicit Workspace ownership, relational constraints, transactions, and rebuildable projections are preserved.
- ADR-0004: UUID identities, immutable full revisions, current pointer/version, conflicts, restoration lineage, and idempotency are preserved.
- ADR-0005: Account, Workspace grant, staff/administrator separation, sessions, recent authentication, and bounded security events remain distinct.
- ADR-0006: Scene Revision alone contains authoritative normalized plain-text body content and representation versions.

### Architecture alignment

The recommendation follows the data model's typed concepts and Workspace root, the security model's server authorization, the AI model's non-authoritative suggestions, the integration model's bounded providers, and export/backup/restoration invariants.

### Normative-document impact

If accepted, the data-model, security, export, backup, and restoration documents should be reconciled with the selected narrow core and a later physical-schema ADR should define implementation. The ADR index should then be updated. No normative document is changed by this Proposed ADR.

## Migration and Portability

Stable UUIDs, explicit Workspace relationships, complete revision snapshots, constrained lifecycle, explicit order, and typed provenance references are portable across supported Django/PostgreSQL versions and future relational systems.

Physical migration preserves Account-to-Workspace grants, Workspace identity, Scene identity, every Scene Revision, current pointer/version, exact content and representation versions, lineage, lifecycle, order, provenance, and supporting references. Database row IDs, tuple locations, sequences, timestamps, and index order are not portable identity.

Old Story Engine records are untrusted import sources. They receive new Strange Novelty IDs and explicit Workspace ownership where appropriate, preserve source IDs as provenance, enter Imported state, and never import old settings, secrets, sessions, or implied Canon. Old chapters/snapshots do not automatically form a valid revision chain.

Restoration of the same archive preserves identities and exact authoritative relationships. Import into another Workspace creates new identities unless a later approved operation proves same-archive restoration. Derived data may be rebuilt.

Future Characters, Locations, hierarchy, Links, states, Claims, attachments, AI suggestions, and integrations receive explicit typed tables or bounded supporting models through later decisions; they do not require migration into a universal content table.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Define the exact first vertical slice and hierarchy dependency for Scene.
- [ ] Decide supported Django Account reference/custom-user boundary before first migration.
- [ ] Define Workspace and grant lifecycle, uniqueness, and Version 1 owner rules.
- [ ] Define the physical Workspace, Grant, Scene, Scene Revision, and provenance schema in a later ADR.
- [ ] Decide whether UUIDs are physical primary keys or separately unique application identities.
- [ ] Decide empty-Scene/current-revision null semantics.
- [ ] Define which Scene mutations advance the integer version.
- [ ] Prototype same-Workspace composite keys/constraints with supported Django/PostgreSQL.
- [ ] Define lineage/base/restoration/provenance cardinalities.
- [ ] Select a small lifecycle vocabulary and transition graph.
- [ ] Evaluate ordering algorithms with synthetic insert/move/reorder/concurrency tests.
- [ ] Define provenance baseline fields and source-specific record boundaries.
- [ ] Classify which future child/supporting records repeat Workspace identity.
- [ ] Define immutable-revision database/service enforcement and emergency repair.
- [ ] Define lifecycle-aware uniqueness and deletion/cascade policies.
- [ ] Define derived-data source linkage, invalidation, and rebuild contracts.
- [ ] Define import, AI apply, restore, migration, and administrative source services.
- [ ] Define export/archive and backup representation for grants, lifecycle, order, revisions, and provenance.
- [ ] Define isolated restoration validation for every core invariant.
- [ ] Decide whether PostgreSQL RLS merits a separate defense-in-depth ADR after deployment design.
- [ ] Define purge only after retention, backup, and recovery policies are accepted.
- [ ] Add physical-schema, transaction, authorization, cross-Workspace, migration, export, backup, and restoration tests later.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes Django initialization, application code, models, migrations, SQL, fixtures, admin registration, forms, views, APIs, serializers, commands, tests, database objects, package installation, field lengths, indexes, constraint names, table names, role vocabulary, purge workflow, ordering algorithm, provenance payload schema, production-data access, deployment, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No Django project, model, migration, SQL, fixture, admin registration, form, view, API, serializer, command, test, database object, package, table, index, constraint, role, ordering key, or deployment configuration is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
