# Architecture Work Session — 2026-07-11

This file is an informational session handoff note. It is not an ADR and is not normative. Accepted ADRs and normative architecture documents take precedence if anything here conflicts with them.

- Repository: `/home/burmuss/projects/strange-novelty`
- Working branch: `main`
- Reference-only repository: `/home/burmuss/projects/the-story-engine` — it must never be modified.

## Session Purpose

This session established foundational architecture decisions before Django initialization or application implementation. The work converted major deployment, runtime, persistence, identity, concurrency, authentication, content-representation, and logical-schema questions into reviewed and accepted ADRs while deliberately deferring physical implementation.

The resulting foundation is intended to make the first private writing workflow secure, recoverable, portable, and consistent with authorial control before models, migrations, packages, or deployment choices constrain it.

## Completed Decisions

### ADR-0001: Deployment and Trust-Boundary Model

- Status: Accepted
- Decision date: 2026-07-11
- Decision: Strange Novelty is a private web application. The browser is untrusted, the Django server is the policy boundary, and external services and background jobs receive only bounded authority. Private content never becomes public merely through possession of an identifier or URL.
- Implementation implications: Every private request must cross server-side authentication, authorization, Workspace scoping, validation, and safe persistence boundaries. Browser code cannot connect directly to authoritative storage or hold provider secrets. Jobs must revalidate current state before effects.
- Deliberately undecided: Exact hosting provider, deployment topology, process layout, browser/frontend technology, job infrastructure, secret-management product, and operational environment.

### ADR-0002: Application Runtime and Framework

- Status: Accepted
- Decision date: 2026-07-11
- Decision: Use a supported CPython runtime and Django in a modular monolith, with server-rendered pages as the baseline and progressive enhancement where it earns its complexity.
- Implementation implications: Django application/query services own policy and domain operations. The initial system should have one deployable application boundary and avoid client-side duplication of authorization or business rules.
- Deliberately undecided: Exact Python and Django versions, frontend package/framework, ASGI/WSGI server, dependency versions, module layout, deployment process, and which interactions require enhancement.
- Explicitly avoided: A premature SPA, microservices architecture, or desktop-primary application.

### ADR-0003: Primary Database and Physical Persistence

- Status: Accepted
- Decision date: 2026-07-11
- Decision: PostgreSQL is the authoritative structured relational database. The browser never connects directly. Private records have explicit Workspace ownership, and transactions, constraints, controlled migrations, backups, and restoration verification protect integrity.
- Implementation implications: Django mediates database access; multi-record writes use explicit transactions; constraints reinforce stable identity, Workspace scope, relationships, and history. Search indexes, caches, backlinks, and similar projections remain rebuildable.
- Deliberately undecided: Exact PostgreSQL version/host, physical schema, indexes, database roles, connection pooling, migration details, row-level security, backup destination/format, and operational topology.

### ADR-0004: Stable Identifiers, Revisions, and Optimistic Concurrency

- Status: Accepted
- Decision date: 2026-07-11
- Decision: Use application-generated UUID identity under the accepted preferred/fallback strategy. Scene and Scene Revision are distinct. Scene Revisions are immutable complete snapshots; Scene points to the current revision and carries an integer version. Saves use both values for optimistic concurrency, without silent last-write-wins or automatic merge. Restore creates a new revision.
- Implementation implications: Revision insertion and current-pointer/version advancement are atomic. A stale or failed save creates no authoritative revision. Ambiguous retries use bounded idempotency. IDs survive rename, hierarchy moves, export, restoration, migration, and provider changes.
- Deliberately undecided: Complete schema, exact UUID implementation selection at implementation time, conflict-draft storage, idempotency retention, transaction/locking details, job infrastructure, and display revision numbering.

### ADR-0005: Authentication, Sessions, Authorization, MFA, and Account Recovery

- Status: Accepted
- Decision date: 2026-07-11
- Decision: Version 1 uses one locally managed Django owner account, no public registration, and no mandatory external identity provider. A strong password remains supported, with required WebAuthn MFA before real private content and bounded TOTP fallback. Sessions are revocable and database-backed. Authorization is explicit and Workspace-scoped. High-impact actions require recent authentication. Recovery uses additional authenticators and one-time recovery codes with documented break-glass handling.
- Implementation implications: Session cookies are protected and opaque; CSRF remains enabled; sessions can be reviewed and revoked; account recovery cannot become an easier bypass than login. Django staff/superuser and database administration do not imply creative approval or Canon authority.
- Deliberately undecided: Exact account model, password values/hasher tuning, WebAuthn/TOTP packages and details, cookie settings, timeout windows, rate limits, bootstrap mechanism, notifications, email provider, and emergency-recovery procedure.

### ADR-0006: Scene Content Representation and Editor Persistence Boundary

- Status: Accepted
- Decision date: 2026-07-11
- Decision: Normalized UTF-8 plain text is the authoritative content of each Scene Revision. Markdown, HTML, browser DOM, and editor-native JSON are not authoritative. Normalization is deterministic and versioned while preserving creative whitespace and punctuation. Saves submit complete content. Browser drafts remain non-authoritative.
- Implementation implications: Scene Revision stores content-format and normalization versions. Rendering, search, excerpts, counts, AI context, and exports are derived from identified source revisions. A saved state follows server acknowledgment. Future rich text requires a later ADR and migration that preserves every revision and recovery invariant.
- Deliberately undecided: Unicode normalization form, canonical line endings, limits, paste transformation, editor/frontend packages, autosave, browser-draft storage, rendering/search/count algorithms, export formats/libraries, and migration tooling.

### ADR-0007: Core Domain Schema and Workspace-Scoped Record Model

- Status: Accepted
- Decision date: 2026-07-11
- Decision: Use an explicit relational core. Account, Workspace, Workspace Grant, Scene, and Scene Revision are distinct. Shared PostgreSQL tables use direct Workspace foreign keys on aggregate roots and important history records. Scene is the mutable aggregate root; Scene Revision is immutable content history. Lifecycle is constrained, ordering explicit, provenance separate from lineage, Canon, and security audit, and supporting infrastructure remains separate.
- Implementation implications: Same-Workspace relationships should be constrained where feasible. Scene holds no second authoritative body. Current pointer/version rules remain atomic. PostgreSQL constraints reinforce structure while Django services remain responsible for authorization and creative meaning.
- Deliberately undecided: Exact models/tables/fields, migrations/SQL, UUID key layout, empty-Scene behavior, version-advance rules, lifecycle vocabulary, ordering algorithm, provenance representation, indexes/constraints, retention/purge, row-level security, packages, and deployment.

## Locked Architecture Invariants

- The browser is untrusted.
- All authoritative access passes through Django application and query services.
- PostgreSQL is authoritative for structured relational state.
- Every private operation is authenticated, authorized, explicitly Workspace-scoped, and revalidated server-side.
- Cookie-authenticated state changes remain CSRF-protected.
- Identifiers, URLs, session IDs, CSRF tokens, consistency tokens, recovery codes, idempotency keys, and possession of records do not independently grant domain authority.
- Stable application IDs survive rename, move, export, restoration, migration, and provider changes.
- Account identity, Workspace identity, and Workspace authorization are distinct.
- Django staff/superuser or database-administrator capability is not ordinary creative authority.
- No authoritative manuscript body exists outside Scene Revision.
- Scene and Scene Revision have distinct stable identities.
- Scene Revisions are immutable, append-oriented, complete snapshots.
- Scene current-revision pointer and integer version select and protect current state.
- Saves are atomic and optimistic-concurrency protected.
- Failed, invalid, or stale saves create no authoritative revision.
- No silent last-write-wins or automatic merge is permitted.
- Browser drafts and rejected conflict drafts are not Scene Revisions.
- Restoring older Scene content creates a new revision rather than changing history.
- Authoritative Scene content is normalized UTF-8 plain text with explicit format and normalization versions.
- AI output is suggestion data and gains no authority without explicit owner action through ordinary mutation rules.
- Derived rendering, search data, counts, excerpts, backlinks, previews, and caches are rebuildable.
- Derived records identify their authoritative source where retained and never become the only copy.
- Exports are not backups.
- Restoration preserves stable identity, complete revision history, current pointers, provenance, and exact authoritative content.
- Provenance records origin; it does not imply Canon, truth, quality, or approval.
- Authoring-source category is distinct from creative authority.
- Supporting jobs, imports, AI operations, exports, backups, restoration runs, authentication records, and security events grant no domain authority merely by reference.
- Manuscript content must not enter routine logs, URLs, query strings, traces, analytics, metrics labels, exception telemetry, or security events.
- The old Story Engine remains reference-only and immutable.

## Deliberately Undecided

### Runtime and deployment

- Exact supported Python, Django, PostgreSQL, browser, and package versions.
- Deployment topology, hosting provider, process/server arrangement, network exposure, and operating environment.
- Secret-management product, configuration delivery, key custody, monitoring, incident operations, and production access.
- Production database hosting, pooling, roles, storage topology, and update procedures.

### Authentication

- Exact custom-user or supported Django Account implementation.
- WebAuthn and TOTP packages and detailed ceremony policies.
- Password minimums, compromised-password screening implementation, hasher selection, and tuning.
- Cookie names/settings, session idle and absolute timeouts, and recent-authentication windows.
- Initial-owner bootstrap mechanism and evidence.
- Rate-limit values, notification channels, email provider, and documented break-glass recovery procedure.

### Content and editor

- Unicode normalization form and Unicode-version compatibility policy.
- Canonical internal and export line endings.
- Request and content-size limits.
- BOM, control-character, bidirectional-control, and pasted-HTML conversion rules.
- Editor package, frontend framework, and supported browser matrix.
- Autosave behavior, local browser-draft technology, retention, and conflict-recovery UX.
- Rendering, sanitization where needed, count/search algorithms, comparison behavior, and export libraries.

### Physical schema

- Exact table and column names, types, lengths, nullability, and physical key choices.
- UUID primary-key/application-key arrangement.
- Exact Django models, managers, validators, migrations, and SQL.
- Index definitions, uniqueness, foreign-key/check constraints, names, and deferrability.
- Empty-Scene and null current-revision semantics.
- Which Scene mutations advance the integer version.
- Lifecycle vocabulary, transition graph, timestamps, and visibility rules.
- Ordering algorithm and rebalance/concurrency behavior.
- Provenance table/operation shape and bounded metadata schema.
- Deletion retention, cascade, purge, backup-expiry, and recovery policy.
- Optional PostgreSQL row-level security and its job/admin/restoration implications.

### Supporting systems

- Background-job runner, queue, dispatch, retry, cancellation, and service identities.
- Idempotency-record schema, fingerprints, state, retention, and cleanup.
- Search implementation, derived projections, consistency, rebuild, and repair.
- Import formats, staging schema, validation, transformation, and legacy migration.
- AI provider gateway, provider selection, operation/suggestion persistence, context manifests, limits, and retention.
- Human-readable export and structured archive formats, manifests, integrity, and compatibility.
- Backup scope, destination, encryption, retention, verification, and recovery objectives.
- Restoration-run schema, isolated environment, validation, activation, and rollback.
- Security-event schema, integrity, access, retention, alerting, and privacy boundaries.
- External integration providers, grants, synchronization, provenance, disconnection, and failure behavior.

## Work Not Yet Authorized

Accepted ADRs establish durable architecture but do not yet authorize:

- Django project initialization;
- application code;
- Django models or migrations;
- SQL or PostgreSQL objects;
- package installation;
- fixtures, constraints, indexes, or tests;
- forms, views, APIs, serializers, templates, JavaScript, or CSS;
- job, search, AI, import, export, backup, or restoration implementation;
- deployment or production provisioning;
- production-data access; or
- any modification of `/home/burmuss/projects/the-story-engine`.

## Recommended Next ADRs

1. **Physical Schema, Constraints, and Initial Migration Boundary.** Translate ADR-0007 into implementable relational structures and migration order without writing models yet.
2. **Backup, Structured Archive Export, and Restoration Verification.** Define what complete recovery means and ensure the initial schema can be exported, backed up, verified, and restored.
3. **Background Jobs, Idempotency Records, and Transactional Dispatch.** Establish bounded asynchronous authority and safe post-transaction work before AI, export, or restoration jobs depend on it.
4. **Search and Derived Projection Architecture.** Define rebuildable indexing, freshness, authorization, and source-revision linkage.
5. **AI Provider Gateway, Context Manifest, and Suggestion Persistence.** Select the provider-independent operation boundary, narrow context evidence, non-authoritative results, and retention.
6. **Import and Legacy Story Engine Migration Boundary.** Define staged untrusted transformation, provenance, identity mapping, and explicit owner review before legacy access is attempted.
7. **Operational Deployment, Secrets, Logging, and Recovery Procedures.** Select deployable infrastructure only after application/data/recovery boundaries are precise enough to evaluate it.

The physical-schema ADR should come next because ADR-0007 now defines the logical records and invariants that models and migrations must implement. It should decide how PostgreSQL and Django can enforce those boundaries before framework initialization creates durable defaults. Backup, structured archive, and restoration requirements must influence that schema before models are implemented; otherwise identity, history, lifecycle, provenance, and recovery fields could be added too late or inconsistently.

## Immediate Next Step

The next practical action is to draft and review a Proposed physical-schema ADR, not to initialize Django.

Recommended working title:

**ADR-0008: Physical Schema, Constraints, and Initial Migration Boundary**

Likely decision areas:

- supported custom-user or Account-reference boundary;
- UUID primary-key arrangement;
- Workspace and Workspace Grant tables;
- Scene and Scene Revision fields;
- null current-revision behavior and empty-Scene semantics;
- composite same-Workspace integrity;
- circular Scene/current-revision creation strategy;
- predecessor, base, restoration, operation, and provenance references;
- lifecycle fields and constrained states;
- ordering-field strategy;
- immutable-revision enforcement;
- deletion behavior and relationship protection;
- initial migration sequencing; and
- backup, archive export, and restoration implications.

ADR-0008 should remain logical-to-physical design documentation. It should not create models, migrations, SQL, or database objects during drafting or acceptance.

## Working Method

1. Codex drafts one Proposed ADR and no other file.
2. The owner reviews the ADR in manageable terminal chunks.
3. Acceptance is a separate Codex edit.
4. The ADR index is updated only upon acceptance.
5. The owner runs `git diff --check`.
6. The accepted ADR and index are committed together.
7. The working tree is confirmed clean before the next ADR.
8. Application implementation remains deferred until prerequisite ADRs are accepted.

## Repository State

State inspected immediately before creating this note:

- Repository: `/home/burmuss/projects/strange-novelty`
- Branch: `main`
- Latest commit: `12c3f8d Accept core domain and workspace-scoped schema model`
- Working tree before note creation: clean
- Accepted ADR range: ADR-0001 through ADR-0007, all Accepted with decision date 2026-07-11
- Intended uncommitted state after note creation: only `docs/notes/architecture-work-session-2026-07-11.md`

This state is a point-in-time observation, not a durable architectural decision. Run Git commands again when resuming.

## Handoff Checklist

- [ ] Confirm the repository is `/home/burmuss/projects/strange-novelty`.
- [ ] Confirm the branch is `main`.
- [ ] Run `git status` before making changes.
- [ ] Read this session note as informational context.
- [ ] Read `docs/decisions/README.md` and applicable normative architecture documents.
- [ ] Treat ADR-0001 through ADR-0007 as Accepted.
- [ ] Do not reopen accepted decisions without an explicit amendment or superseding ADR.
- [ ] Continue with Proposed ADR-0008.
- [ ] Keep `/home/burmuss/projects/the-story-engine` read-only.
- [ ] Do not initialize Django prematurely.
- [ ] Preserve unrelated work and keep the next change narrowly scoped.
