# Strange Novelty Version 1 Implementation Roadmap

## Purpose

This planning document translates accepted ADR-0001 through ADR-0015 into an ordered, dependency-aware implementation plan for Strange Novelty Version 1. It is not an ADR, does not change any accepted decision, and does not authorize implementation by itself.

The plan favors small vertical slices that produce reviewable behavior while establishing security, identity, history, recovery, and operational foundations in the order they are needed. Dates and effort estimates are intentionally absent until the implementation team, supported versions, and deployment constraints are known.

## Planning Principles

1. Preserve the browser/Django/PostgreSQL authority boundary in every slice.
2. Deliver working owner-visible behavior early rather than building all infrastructure before the Scene editor.
3. Establish stable identity, Workspace scope, immutable history, and concurrency before convenience features.
4. Treat authorization, privacy, accessibility, tests, migrations, and failure behavior as deliverables, not cleanup.
5. Keep derived data, imports, AI output, and browser drafts non-authoritative.
6. Use one Django modular monolith with distinct web, worker, migration, backup, and restore roles.
7. Keep changes small enough for independent review, rollback analysis, and focused verification.
8. Resolve deferred implementation choices only when their latest responsible phase approaches.
9. Use synthetic data in development and tests; never depend on production or Story Engine private data.
10. Do not claim readiness until backup restoration and operational procedures have been exercised.

## Accepted Architecture Baseline

| ADR | Implementation baseline |
| --- | --- |
| ADR-0001 | Private authenticated web application; untrusted browser; Django-side authority |
| ADR-0002 | Supported CPython and Django; server-rendered modular monolith; progressive enhancement |
| ADR-0003 | PostgreSQL authority; explicit Workspace scope; constraints, transactions, migrations, recovery |
| ADR-0004 | Application-generated UUIDs; Scene/current Revision/version; immutable snapshots; optimistic concurrency |
| ADR-0005 | Local owner Account; required MFA before private content; revocable server sessions; explicit authorization |
| ADR-0006 | Normalized UTF-8 plain-text Scene Revision content; complete-content saves; derived rendering |
| ADR-0007 | Explicit Account, Workspace, Grant, Scene, Revision, lifecycle, ordering, provenance boundaries |
| ADR-0008 | Custom Account before first migration; native UUID core; initial empty revision; physical constraints |
| ADR-0009 | Human export, portable archive, database backup, isolated verified restoration, controlled activation |
| ADR-0010 | PostgreSQL-backed Jobs, Attempts, idempotency, leases, retries, cancellation, reconciliation |
| ADR-0011 | Server-side AI gateway; staged Suggestions; explicit human application; stale-source checks |
| ADR-0012 | PostgreSQL full-text search; rebuildable current-Scene projections; asynchronous indexing |
| ADR-0013 | Staged one-way import; new target UUIDs; mappings; validation, approval, atomic application |
| ADR-0014 | Isolated environments; validated configuration; secret/role separation; observable, recoverable releases |
| ADR-0015 | HTML-first private HTTP; complete POST saves; dual preconditions; idempotency; manual conflicts |

All implementation must also preserve product and architecture requirements for privacy, authorial control, meaningful content states, provenance, portability, recovery, and bounded AI context.

## Version 1 Scope

This roadmap covers the accepted architectural foundation and the first coherent private writing workflow:

- one locally managed owner Account and one initial private Workspace;
- secure authentication, session, MFA, recovery, and Workspace authorization;
- Scene creation, listing, editing, lifecycle, ordering, immutable revisions, and provenance;
- server-rendered editor with explicit save, optimistic concurrency, idempotency, and manual conflict recovery;
- bounded security and operational evidence;
- durable Jobs and worker execution;
- PostgreSQL full-text Scene search through rebuildable projections;
- author-readable export, structured archive, database backup, isolated restoration, and verification;
- staged legacy Story Engine import with new identities and owner approval;
- one narrow scene-focused AI review producing non-authoritative Suggestions;
- production configuration, secrets, deployment, observability, incident, and recovery readiness.

The product documents also name Characters, Locations, Links/backlinks, hierarchy, and broader content-state behavior as Version 1 goals. ADR-0001 through ADR-0015 do not yet define their complete logical/physical/interaction models. Those capabilities require focused decisions and roadmap refinement before implementation; this document does not invent them.

## Explicitly Deferred Scope

- public sign-up, public sharing, teams, invitations, collaboration, and a general role marketplace;
- a public API and API-first frontend architecture;
- SPA-only correctness, desktop-primary architecture, and independently deployed microservices;
- external search engines, semantic/vector search, embeddings, recommendations, and RAG beyond accepted bounded context selection;
- autonomous agents, provider tools, web browsing, arbitrary file access, and automatic AI application;
- rich text, authoritative Markdown/HTML/editor JSON, and automatic conflict merge;
- attachments, artwork/object storage, publishing integrations, and broad external integrations;
- local-first synchronization, required durable browser drafts, and offline mutation queues;
- partial restore, automatic cross-Workspace merge, and direct legacy database reuse;
- performance optimization unsupported by measurements.

## Delivery Phases

Phases are dependency ordered, but small follow-up work may overlap after a phase’s blocking interfaces and tests are stable. Each phase ends in independently reviewable evidence. Milestones group related phase outcomes; they do not permit skipping phase exit criteria.

## Phase 0: Repository and Development Foundation

### Objective

Create a reproducible, documentation-aligned development foundation without making production claims.

### ADRs implemented

ADR-0002 and the local/non-production portions of ADR-0014; repository safety from ADR-0001 and ADR-0003.

### Prerequisites

Accepted ADR-0001 through ADR-0015; resolution of supported Python/Django/PostgreSQL versions and dependency tooling.

### Concrete deliverables

- documented project bootstrap and dependency workflow;
- initial Django project/app layout aligned with the modular monolith;
- validated local and test configuration contracts with safe defaults;
- synthetic-data-only test policy and repository ignore protections;
- formatting, linting, unit-test, and documentation-check commands;
- release/source identity interface sufficient for later operations.

### Database and migration work

None yet. Do not run the first Django migration until the custom Account model and initial migration plan are ready in Phase 1.

### Application services

Only package/module boundaries and interfaces; no domain behavior.

### HTTP or UI work

A minimal non-private development landing/health surface may prove startup, but no manuscript or authentication feature.

### Background work

None; reserve worker entry-point boundaries without implementing a queue.

### Tests

Configuration parsing/fail-closed tests, project startup checks, dependency/reproducibility checks, and a no-production-data test convention.

### Security checks

Secret-pattern and committed-artifact review; ensure browser assets expose no server configuration; confirm debug behavior cannot be mistaken for production.

### Operational checks

Document local startup and teardown; record supported toolchain; ensure failure messages do not print secrets.

### Acceptance criteria

A clean checkout can reproducibly create the local/test environment and run checks without production credentials or private data.

### Explicit non-goals

Models, migrations, owner accounts, production containers, cloud resources, and deployment automation.

### Exit criteria

Project layout and configuration contract are reviewed; the first migration remains unrun; Phase 1 version/tooling decisions are recorded.

## Phase 1: Django and PostgreSQL Foundation

### Objective

Establish the custom Account boundary and initial PostgreSQL schema in the accepted dependency order.

### ADRs implemented

ADR-0002, ADR-0003, ADR-0007, ADR-0008, and relevant ADR-0014 migration/configuration boundaries.

### Prerequisites

Phase 0; exact supported versions; PostgreSQL local/test connectivity; custom-user/account reference decision resolved before any migration.

### Concrete deliverables

- custom Django Account model established before the first migration;
- explicit Workspace, Workspace Grant, Mutation Operation, Scene, and Scene Revision models;
- native UUID primary identities generated before persistence;
- lifecycle/order/version/current-pointer/content/provenance boundaries matching ADR-0008;
- reviewed migration sequence that resolves the Scene/current-Revision circular dependency;
- database-role interfaces for later least-privilege deployment.

### Database and migration work

Create ordered foundational migrations: Account; Workspace; Grant; Mutation Operation if selected in the initial core; Scene base; Scene Revision; current pointer; same-Workspace/lineage/lifecycle/order constraints. Use the accepted initial-empty-revision creation model. Review generated SQL and constraint coverage.

### Application services

Minimal repository/query primitives that require explicit Workspace scope; UUID generation; invariant helpers; no browser editing yet.

### HTTP or UI work

None beyond development diagnostics protected from private data.

### Background work

None.

### Tests

Migration-from-empty tests; constraint tests; cross-Workspace rejection; current-pointer/Revision consistency; immutable history application-path tests; protective deletion tests; migration rollback/forward behavior where supported.

### Security checks

Confirm Account disablement cannot cascade Workspace data; no database credentials reach the browser; no universal runtime superuser assumption.

### Operational checks

Migration is explicit and serialized; startup does not migrate; schema state is observable; local backup/restore implications are documented before destructive migration work.

### Acceptance criteria

An empty PostgreSQL database migrates deterministically to the reviewed core schema and rejects invalid cross-Workspace/current-pointer relationships.

### Explicit non-goals

Complete authentication UI, MFA, editor, Jobs, search, imports, AI, and production deployment.

### Exit criteria

The initial schema and migration evidence are reviewed; no default Django user-model migration preceded the custom Account.

## Phase 2: Account, Authentication, and Workspace Bootstrap

### Objective

Provide secure owner enrollment, login/logout, sessions, Workspace bootstrap, and explicit owner Grant authorization.

### ADRs implemented

ADR-0001, ADR-0005, ADR-0007, ADR-0008, and security/configuration portions of ADR-0014.

### Prerequisites

Phase 1; authentication, WebAuthn, and bounded TOTP package decisions; password/session/CSRF policy values; protected bootstrap design.

### Concrete deliverables

- one-time protected owner bootstrap disabled after enrollment;
- local password authentication using maintained Django interfaces;
- required WebAuthn enrollment before real private content, with multiple authenticators/recovery codes;
- bounded TOTP fallback where selected;
- database-backed revocable named sessions and session review/revocation;
- explicit Account-to-Workspace owner Grant;
- recent-authentication hooks for sensitive actions;
- password/MFA recovery and bounded emergency-recovery interfaces.

### Database and migration work

Authentication factor, recovery verifier, session metadata, Grant-state, and bounded Security Event migrations as required; no plaintext secrets or recovery codes.

### Application services

Bootstrap, authentication, Workspace authorization, recent-authentication, session revocation, recovery, and generic enumeration-resistant response services.

### HTTP or UI work

Server-rendered enrollment, login, logout, MFA, recovery-code presentation, recovery, session review, and Workspace landing pages; CSRF on every state change.

### Background work

None required; notification delivery remains deferred unless a later selected channel requires Jobs.

### Tests

Bootstrap one-time behavior; password validation; MFA enforcement/removal; recovery-code one-time hashing; session rotation/revocation; CSRF; enumeration resistance; Workspace Grant revocation; accessibility of forms/errors.

### Security checks

Threat review for takeover and recovery abuse; cookie settings; rate-limit interface; no secrets in logs; staff/superuser cannot substitute for Workspace or creative authority.

### Operational checks

Document owner bootstrap, credential rotation, session revocation, and emergency recovery; test disabling an Account preserves the archive.

### Acceptance criteria

The owner can enroll once, authenticate with required factors, enter only the authorized Workspace, review/revoke sessions, and recover without an email-only MFA bypass.

### Explicit non-goals

Public registration, teams, invitations, social login, delegated identity, and creative content editing.

### Exit criteria

Secure owner login and Workspace authorization pass automated and manual security/accessibility checks.

## Phase 3: Core Scene and Revision Domain

### Objective

Deliver invariant-preserving Scene creation and immutable revision services before editor autosave or asynchronous behavior.

### ADRs implemented

ADR-0003, ADR-0004, ADR-0006, ADR-0007, and ADR-0008.

### Prerequisites

Phases 1 and 2; Unicode normalization form and line-ending rule; initial content/size policy values; Scene lifecycle/order labels and version-advance rules.

### Concrete deliverables

- Workspace-scoped Scene creation with initial empty Revision;
- immutable complete normalized UTF-8 Scene Revisions;
- current pointer, integer Scene version, revision number, lifecycle, sparse order, and provenance;
- ordinary save/restore service using one atomic transaction;
- deterministic validation/normalization and derived count interfaces;
- protective trash/archive behavior without physical purge.

### Database and migration work

Complete/refine Scene/Revision constraints and indexes justified by measured queries; add format/normalization/version checks and lineage/restoration references without weakening initial migrations.

### Application services

Create Scene, load current Scene, save complete content, restore prior content as a new Revision, lifecycle transition, and reorder services. Every service requires actor and Workspace and creates appropriate Mutation Operation provenance.

### HTTP or UI work

Minimal server-rendered Scene list/detail/create interfaces may begin the first vertical slice; editing save behavior completes in Phase 4.

### Background work

None.

### Tests

Normalization fixtures; exact whitespace preservation; initial empty Revision; atomic revision/pointer/version; stale service call creates no Revision; restore creates a new Revision; lifecycle/order rules; cross-Workspace denial; property tests for invariants where valuable.

### Security checks

No manuscript content in logs/errors; output escaping; request-independent service authorization; UUID possession grants no access.

### Operational checks

Migration/backup scope identifies every authoritative field; synthetic database restore preserves exact content and pointers.

### Acceptance criteria

Authorized services can create and revise a Scene while preserving immutable exact history, provenance, Workspace scope, and atomic current state.

### Explicit non-goals

Autosave, automatic merge, rich text, purge, AI, search, import, and background execution.

### Exit criteria

Core Scene service tests prove all ADR-0004/0006/0008 invariants and support the Phase 4 HTTP adapter.

## Phase 4: Editor Load, Save, and Conflict Handling

### Objective

Deliver the first complete owner-visible Scene writing workflow with explicit save and manual conflict recovery.

### ADRs implemented

ADR-0001, ADR-0004, ADR-0005, ADR-0006, ADR-0015, and relevant ADR-0014 privacy/error boundaries.

### Prerequisites

Phase 3; canonical request fingerprint rules; initial request/content limits; private cache policy; accessible editor/error design.

### Concrete deliverables

- server-rendered Scene list, create, editor load, and explicit save;
- load contract with Scene ID, current Revision ID, Scene version, lifecycle, and authoritative text;
- complete-content POST with both expected values and idempotency key;
- confirmed success/redirect behavior and new preconditions;
- conflict response preserving submitted draft and showing authorized current text;
- manual reconciliation path with no force overwrite;
- optional progressive-enhancement seam, not autosave yet.

### Database and migration work

Only durable idempotency storage required for save retries if not already present; no editor-state or conflict-draft table in the first slice.

### Application services

HTTP adapters invoke the Phase 3 mutation service plus scoped idempotency reconciliation, authentication, authorization, lifecycle, validation, and CSRF enforcement.

### HTTP or UI work

HTML-first forms, field errors, Post/Redirect/Get, generic access errors, no-store/private headers, unsaved/saving/saved/conflict/failure text, keyboard and assistive-technology behavior.

### Background work

None. Browser request cancellation is not a Job cancellation or transaction rollback.

### Tests

GET safety; CSRF; authentication/authorization; complete POST; dual-precondition conflicts; duplicate delivery; timeout-after-commit reconciliation; multi-tab response order; validation; caching; escaping; JavaScript-disabled and accessibility tests.

### Security checks

No content in URLs/logs/metrics/Security Events; non-disclosure for inaccessible IDs; safe rendering; bounded bodies/frequency; session expiry rechecks current state.

### Operational checks

Privacy-safe correlation/error categories; health/maintenance behavior does not expose content; error paths preserve authoritative data.

### Acceptance criteria

The owner can create, load, edit, save, reload, and manually resolve a stale edit without losing newer content or creating duplicate Revisions.

### Explicit non-goals

Autosave, automatic merge, durable local drafts, offline synchronization, public API, frontend framework, and rich text.

### Exit criteria

The working Scene editor passes concurrency, privacy, accessibility, and JavaScript-disabled acceptance tests.

## Phase 5: Security Events, Mutation Operations, and Audit Boundaries

### Objective

Make security evidence, creative provenance, operational logs, and execution evidence explicit and non-overlapping.

### ADRs implemented

ADR-0005, ADR-0007, ADR-0008, ADR-0010, ADR-0011, and ADR-0014.

### Prerequisites

Phases 2 through 4; bounded event vocabularies, identifiers, retention interfaces, and access rules.

### Concrete deliverables

- immutable/bounded Mutation Operation provenance for accepted domain mutations;
- Security Event records for authentication, recovery, authorization, administrative, and high-impact outcomes;
- privacy-minimized structured operational logging schema;
- safe correlation across records without collapsing their meanings;
- protected owner/operator review interfaces where justified.

### Database and migration work

Complete Mutation Operation and Security Event tables/constraints/indexes; protective references; retention fields without manuscript payload columns.

### Application services

Central event/provenance creation interfaces with allowlisted fields and transaction coupling appropriate to the event type.

### HTTP or UI work

Bounded session/security review and provenance display; no raw operational-log browser.

### Background work

Cleanup interfaces only; execution waits for Phase 6 Jobs.

### Tests

Event classification, transaction coupling, redaction, access, immutability/protection, correlation, and cascade-prevention tests.

### Security checks

Verify passwords, tokens, manuscript text, titles, prompts, queries, paths, cookies, IP/user-agent detail, and recovery plaintext cannot enter prohibited fields.

### Operational checks

Log schema and retention review; simulated security event produces useful bounded evidence without disclosure.

### Acceptance criteria

Every implemented authoritative mutation has provenance, security-relevant actions have bounded Security Events, and routine logs remain separate/private.

### Explicit non-goals

Full compliance program, SIEM vendor, general analytics, event sourcing, or database-admin creative authority.

### Exit criteria

Audit-boundary tests and privacy review pass before Jobs, import, or AI add more evidence sources.

## Phase 6: Jobs, Idempotency, and Worker Runtime

### Objective

Provide durable PostgreSQL-backed asynchronous execution and idempotency before search, import, AI, or automated recovery work relies on it.

### ADRs implemented

ADR-0010 plus service-role, configuration, logging, and restore rules from ADR-0014.

### Prerequisites

Phases 1, 2, and 5; worker polling/claim, lease, heartbeat, retry, retention, concurrency, and shutdown values resolved.

### Concrete deliverables

- Job, append-oriented Job Attempt, durable Idempotency Record, and commit-coupled dispatch/outbox shape;
- constrained Job state machine, atomic claim, lease/heartbeat, cancellation, retries/backoff, terminal/quarantine states;
- worker process using the same application release and bounded service identity;
- progress/result references and privacy-safe operational visibility;
- restore-time lease invalidation and quarantine/reconciliation interfaces.

### Database and migration work

Job/Attempt/Idempotency/dispatch and bounded provider-effect evidence tables, constraints, indexes, retention/protection references.

### Application services

Enqueue-after-commit, claim, renew, complete, retry, cancel, reconcile, manual retry, and cleanup services with Workspace reauthorization.

### HTTP or UI work

Authorized job status/cancel/retry views with generic inaccessible-record behavior; no private payload display.

### Background work

Worker loop, graceful shutdown, bounded polling, safe redelivery, retry classification, and synthetic reference handlers.

### Tests

Commit/dispatch crash windows; duplicate claims; expired leases; worker crash/redelivery; idempotent handler; cancellation checkpoints; ambiguous outcome quarantine; restore reconciliation; authorization revocation; retry storms; cleanup protection.

### Security checks

Least-privileged worker identity/credentials; payload minimization; no service identity as Account/Grant; SSRF/path/object-reference boundaries for future handlers.

### Operational checks

Queue depth/age, stuck leases, terminal counts, worker readiness, graceful drain, alerts, and deployment/restart exercises.

### Acceptance criteria

A synthetic Job survives process failure and duplicate delivery, converges idempotently, respects cancellation/authorization, and is quarantined correctly after simulated restore.

### Explicit non-goals

External broker, distributed workflow engine, microservices, exact-once claims, AI/import/search business handlers.

### Exit criteria

Durable worker semantics and operational evidence pass fault-injection tests; later phases may register handlers without redefining Job semantics.

## Phase 7: Search and Rebuildable Projections

### Objective

Deliver authorized current-Scene full-text search without making the index authoritative.

### ADRs implemented

ADR-0012 using ADR-0010 Jobs and ADR-0006/0007 Scene authority.

### Prerequisites

Phases 3, 4, and 6; PostgreSQL search configuration, projection schema/version, lifecycle eligibility, ranking/snippet limits, and freshness policy resolved.

### Concrete deliverables

- one current-Scene search projection containing source Workspace/Scene/Revision/version and projection version;
- commit-coupled indexing Jobs and conditional publish;
- synchronous invalidation/current marker so stale projections are detectable;
- authorized Workspace-scoped query, lifecycle filters, safe snippets, and freshness indication;
- full rebuild, dual-version reindex, serving cutover, and cleanup commands/services.

### Database and migration work

Projection/search-vector/version fields, PostgreSQL indexes, constraints, and active-version state; no authoritative content duplication.

### Application services

Build/publish/invalidate/query/rebuild/reindex services; every result resolves authorized current Scene state.

### HTTP or UI work

Server-rendered search form/results with no raw query in routine logs or unsafe URLs where avoidable, escaped snippets, archived filter, and stale/incomplete status.

### Background work

Idempotent indexing and rebuild Jobs; restored work is regenerated/quarantined rather than resumed blindly.

### Tests

Workspace isolation; stale worker cannot overwrite new projection; save succeeds if indexing fails; trashed exclusion; archived filter; safe snippets; rebuild equivalence; dual-version cutover/rollback; query limits.

### Security checks

Search existence cannot enumerate inaccessible Scenes; no raw query/snippet telemetry; projection IDs/rank grant no authority.

### Operational checks

Index lag, failures, rebuild duration, projection version, queue depth, storage, and privacy-safe metrics/alerts.

### Acceptance criteria

The owner can find current authorized Scenes; known-stale results are omitted; all projections can be discarded and rebuilt from authoritative PostgreSQL records.

### Explicit non-goals

External/semantic/vector search, embeddings, recommendations, autonomous retrieval, and authoritative snippets.

### Exit criteria

Search, stale-index, recovery, privacy, and rebuild tests pass under representative synthetic content.

## Phase 8: Backup, Archive, and Restore Verification

### Objective

Prove that authoritative state can be backed up, exported, restored in isolation, verified, and activated safely.

### ADRs implemented

ADR-0003, ADR-0009, ADR-0010 restore reconciliation, and ADR-0014 operational boundaries.

### Prerequisites

Phases 1 through 7; backup/archive tool choices, encryption/key custody, retention/schedules, compatibility format, verification report, RPO/RTO targets, and isolated environment design resolved.

### Concrete deliverables

- human-readable current-manuscript export;
- versioned structured Workspace archive with manifest, counts, hashes, IDs, history, pointers, lifecycle, ordering, provenance, and compatibility metadata;
- encrypted multi-generation PostgreSQL backup mechanism;
- isolated restore flow, structural/semantic verification report, session invalidation, Job quarantine, derived rebuild, activation, and rollback path;
- periodic synthetic restore-test procedure and evidence.

### Database and migration work

Export/restore operation evidence as needed; ensure all authoritative tables and migration state are in backup scope; no secrets in portable archives.

### Application services

Authorized export/archive request, manifest generation, verification, restore classification, activation approval, and recovery evidence services.

### HTTP or UI work

Recently authenticated export/restore controls and bounded status/report display; protected artifact access.

### Background work

Export/archive/verification Jobs where appropriate; deployment-specific database backup/restore remains a bounded operational role.

### Tests

Hash/count mismatch; missing/current pointer; cross-Workspace references; exact content/identity/history restoration; incompatible archive failure; session invalidation; Job quarantine; projection rebuild; failed activation rollback.

### Security checks

Encryption in transit/at rest; least-privileged credentials; separate keys; safe filenames; no secrets/session/MFA recovery plaintext in archives/logs; recent authentication and explicit activation.

### Operational checks

Run representative isolated restore, measure evidence against targets, verify multiple generations/expiry, alert on backup and restore-test failure.

### Acceptance criteria

A backup is considered dependable only after a clean isolated restore verifies exact identities, content, relationships, authorization boundaries, and controlled activation behavior.

### Explicit non-goals

Selected-Scene recovery, live unverified restore, immediate backup purge guarantees, provider-specific portability claims.

### Exit criteria

M7 evidence is reviewed before destructive migrations or production launch are allowed.

## Phase 9: Legacy Story Engine Import

### Objective

Provide a safe, staged, owner-reviewed one-way transformation from supported legacy evidence into new Strange Novelty identities.

### ADRs implemented

ADR-0013 using ADR-0006/0008 domain rules, ADR-0010 Jobs, and ADR-0009 recovery boundaries.

### Prerequisites

Phases 3, 5, 6, and 8; supported source format/version, allowlisted parser/isolation, mappings, source limits, lifecycle/order rules, retention, and transaction-size evidence resolved.

### Concrete deliverables

- protected source-artifact intake/inventory;
- Import Batch, staging item, identity mapping, validation/report, dry-run, warning/conflict, and approval records;
- new UUID assignment and deterministic relationship/revision/lifecycle/order mapping;
- trustworthy legacy snapshot reconstruction without fabricated history;
- bounded all-or-nothing application and post-apply provenance;
- quarantine/reconciliation and staging cleanup.

### Database and migration work

Import Batch/staging/mapping/report/source-evidence tables, uniqueness/fingerprint constraints, retention/protective relationships.

### Application services

Ingest, validate, classify, map, preview, approve, apply, cancel, reconcile, and protected reversal-plan services.

### HTTP or UI work

Authenticated source selection, dry-run report, exact count/disposition review, conflicts/warnings, explicit approval, and result views without full-content telemetry.

### Background work

Parsing/validation may use Jobs; apply uses the reviewed bounded transaction. Restored unfinished imports remain quarantined.

### Tests

Malformed/oversized/hostile inputs; encoding; traversal/symlink/archive bomb; duplicate IDs/keys; missing relationships; mapping determinism; no silent merge; all-or-nothing failure; idempotent retry; restore quarantine.

### Security checks

Never execute/deserialise unsafe source code/objects; never follow URLs/paths automatically; exclude credentials/settings/sessions/grants; Workspace reauthorization at approval/apply.

### Operational checks

Import resource budgets, quarantine, artifact protection, retention/cleanup, failure reports, and pre-import recovery point.

### Acceptance criteria

The owner can dry-run and explicitly apply a supported legacy batch into newly identified Imported records with complete mapping/provenance and no silent overwrite or partial authoritative result.

### Explicit non-goals

Live legacy read-through, old-ID reuse, automatic merge, unsupported attachments, broad Story Engine parity, and source authority inheritance.

### Exit criteria

M8 synthetic fixtures and security tests prove staging, identity, revision, atomicity, and recovery behavior.

## Phase 10: AI Suggestion Workflow

### Objective

Deliver one explicitly invoked scene-focused review whose output remains staged until deliberate human application.

### ADRs implemented

ADR-0011 using ADR-0010 Jobs, ADR-0012 bounded search where selected, ADR-0004/0006 mutation rules, and AI-context architecture.

### Prerequisites

Phases 3 through 8; provider/model/SDK, secret injection, prompt/context/output schema versions, source hashes, cost/rate/size limits, retention, and reconciliation API behavior resolved.

### Concrete deliverables

- provider-neutral server adapter and secret boundary;
- AI Request/context manifest referencing exact authorized source Revisions/hashes;
- provider-effect/ambiguous-outcome evidence and normalized AI Suggestion records;
- context preview and explicit submission consent;
- review, reject, expire/delete, edit, partial acceptance, stale warning, regeneration, and explicit application;
- application through ordinary complete-content concurrency mutation with Mutation Operation provenance.

### Database and migration work

AI Request, context source, Suggestion, disposition, usage/cost, bounded provider-effect, and retention fields; no provider secret or full prompt by default.

### Application services

Context selection/authorization, request creation, provider adaptation, response normalization, stale detection, review/disposition, and apply-as-new-Revision services.

### HTTP or UI work

Scene-focused context preview, submit/status, safe suggestion rendering, compare/edit/partial accept, stale-source warning, and application confirmation.

### Background work

AI Jobs with local/provider idempotency, cost/rate controls, cancellation, retry classification, ambiguous-outcome reconciliation, and restore quarantine.

### Tests

Workspace/source scope; unrelated context exclusion; prompt/output validation; provider timeout/ambiguous outcome; duplicate delivery; cost/rate limits; stale source; explicit approval; partial edit; no automatic Canon; restore/retry behavior.

### Security checks

Secrets server-side; minimized context; no full prompts/responses in routine logs/Jobs; output escaped and never executed; SSRF/tool/file/web access disabled.

### Operational checks

Provider degradation leaves core editor ready; bounded usage/cost metrics; secret rotation; terminal/reconciliation review; retention cleanup.

### Acceptance criteria

The owner explicitly requests one bounded review, sees its exact source scope, receives a non-authoritative Suggestion, and can deliberately apply edited content only against current Scene state.

### Explicit non-goals

Autonomous agents, tools, web/file access, automatic application/Canon, broad RAG, embeddings/vector search, and provider-specific domain schema.

### Exit criteria

M9 privacy, stale-source, approval, failure-isolation, cost, and recovery tests pass with synthetic content/provider fixtures.

## Phase 11: Deployment, Operations, and Production Readiness

### Objective

Deploy the verified modular monolith under isolated, least-privileged, observable, recoverable production operations.

### ADRs implemented

ADR-0014 and production implications of ADR-0001 through ADR-0013.

### Prerequisites

All required Version 1 feature phases; M7 verified restore; hosting, secret manager, topology, TLS, process supervision, role grants, telemetry, resource limits, alerts, and operational targets resolved.

### Concrete deliverables

- immutable/reproducible release artifact with source/build/config/migration identity;
- isolated production data/secrets/keys/database/storage/provider credentials;
- separate web, worker, migration, backup, restore, and inspection identities/roles as justified;
- protected transport, validated production configuration, role-specific liveness/readiness, graceful shutdown;
- structured redacted logs, bounded metrics, optional safe tracing, Security Events, alerts;
- maintenance mode, compatibility-aware deployment/rollback, and incident/break-glass controls;
- complete reviewed runbooks.

### Database and migration work

Production role/grant application, serialized migration execution, connection/resource settings, backup integration, and migration compatibility verification; no routine superuser.

### Application services

Maintenance, health/readiness, release/config identity, protected operational actions, and safe diagnostic interfaces.

### HTTP or UI work

Production-safe errors/cache/security headers, owner maintenance/recovery status, and accessible degraded-state behavior.

### Background work

Worker deployment/drain/restart, backup/restore monitoring, cleanup schedules, reindex and reconciliation operations.

### Tests

Release smoke, configuration failure, migration compatibility, rollback, graceful drain, resource exhaustion, provider outage, backup/restore, secret rotation, session revocation, incident, and accessibility regression tests.

### Security checks

Threat model review, dependency/supply-chain evidence, least privilege, TLS/cookies, production debug disabled, secret scanning, telemetry redaction, break-glass exercise, and no production data in non-production.

### Operational checks

Alerts for availability/errors/database/migrations/backups/restores/Jobs/auth anomalies/secrets/storage; capacity review; RPO/RTO/restore-test evidence; on-call/owner procedures.

### Acceptance criteria

A controlled release deploys, migrates once, reports correct readiness, supports critical owner workflows, produces safe telemetry, restores from backup, and rolls back only within declared compatibility.

### Explicit non-goals

Multi-region/high-availability commitments, mandatory staging, vendor-specific lock-in, compliance claims, microservices, and broad collaboration.

### Exit criteria

All Definition of Done items and M10 evidence are reviewed; production activation is explicit and reversible within documented limits.

## Cross-Cutting Test Strategy

- Use a test pyramid: fast domain/unit tests, PostgreSQL integration/constraint tests, Django request tests, worker fault tests, and a small set of end-to-end owner journeys.
- Run PostgreSQL-backed tests for transaction, isolation, constraints, search, migrations, and Jobs; do not substitute an incompatible database.
- Use synthetic manuscript-like fixtures with no private creative material.
- Test Workspace isolation and authorization on every private query/mutation class.
- Include multi-tab races, duplicate delivery, timeout-after-commit, worker crash, restore quarantine, and stale-source cases.
- Test migrations from empty and supported prior schema states, plus structured archive compatibility.
- Test HTML without JavaScript before progressive enhancement.
- Include keyboard, focus, error association, status announcement, zoom, and reduced-motion checks.
- Treat redaction/cache/log/metric tests as required security regression coverage.
- Record verification evidence by milestone rather than relying on an undifferentiated final test run.

## Security Verification Plan

1. Maintain a threat model covering browser, session/CSRF, Workspace isolation, database roles, Jobs, providers, imports, backups, operators, and supply chain.
2. Verify authentication, required MFA, recovery abuse resistance, session rotation/revocation, and recent-authentication gates.
3. Prove every private read/write is Workspace-scoped and unauthorized responses resist enumeration.
4. Test secret absence from Git, browser bundles, logs, metrics, traces, Jobs, archives, and errors.
5. Test content escaping, upload/import parser isolation, request limits, rate controls, and denial-of-service failure behavior.
6. Review database/service least privilege and time-bounded break glass.
7. Verify backup encryption/key separation and isolated activation authorization.
8. Exercise incident containment, session/secret revocation, evidence preservation, and recovery.

## Migration and Data Verification Plan

- Create the custom Account model before migration `0001`; fail review if Django’s default user migration runs first.
- Review migration dependency order, generated SQL, locks, reversibility/forward recovery, and deployment compatibility.
- Validate UUID uniqueness, Workspace composites, current pointers, version/revision numbers, lineage, lifecycle, ordering, provenance, and protective deletion.
- Verify normalization using versioned golden fixtures and exact content round trips.
- Test structured archives against explicit format/schema/content/normalization versions and manifests.
- Restore into isolation and compare counts, identities, hashes, relationships, pointers, authorization boundaries, and representative behavior.
- Rebuild derived search data after restoration; never require projections for authoritative recovery.
- Treat legacy import as new identity creation; preserve source mappings and never masquerade it as restoration.

## Operational Readiness Plan

Production use requires:

- validated environment-specific configuration and external secret/key injection;
- immutable release and dependency identity;
- serialized, observable migrations with compatibility and recovery plan;
- role-specific web/worker liveness, readiness, drain, and capacity limits;
- privacy-minimized logs, bounded metrics, safe errors, Security Events, and alerts;
- encrypted multi-generation backups and a current successful isolated restore exercise;
- Job/AI/search/import reconciliation procedures after restore;
- deployment, migration, rollback, maintenance, backup, restore, rotation, incident, break-glass, and recovery runbooks;
- owner review of RPO, RTO, retention, alerting, and residual risks.

## Dependency Map

| Phase | Direct prerequisites | Blocks |
| --- | --- | --- |
| 0 Repository/development | Accepted ADRs | 1–11 |
| 1 Django/PostgreSQL | 0 | 2–11 |
| 2 Auth/Workspace | 1 | private UI in 3–11 |
| 3 Scene domain | 1, 2 | 4, 7, 9, 10 |
| 4 Editor/conflicts | 3 | owner writing milestone; 7/10 integration |
| 5 Evidence boundaries | 2, 3, 4 | 6, 9, 10, 11 |
| 6 Jobs/worker | 1, 2, 5 | asynchronous 7–10 and production worker operations |
| 7 Search | 3, 4, 6 | search-dependent context; final recovery verification |
| 8 Backup/restore | 1–7 | destructive migrations, import safety, production launch |
| 9 Legacy import | 3, 5, 6, 8 | legacy migration milestone only |
| 10 AI suggestions | 3–8 | AI milestone only |
| 11 Production readiness | required feature phases, especially 8 | production activation |

Character, Location, Link/backlink, hierarchy, and comprehensive content-state work is blocked by additional accepted design decisions and must be inserted before final Version 1 completion where product acceptance criteria require it.

## Milestones

| Milestone | User-visible outcome | Technical outcome | Verification evidence | Blocking dependencies |
| --- | --- | --- | --- | --- |
| M1: Repository and Django foundation | None beyond a reliable development shell | Reproducible Django/PostgreSQL foundation; custom Account before first migration | Clean bootstrap, startup/config, migration-from-empty, constraint tests | Phase 0–1 decisions/tooling |
| M2: Secure owner login and Workspace | Owner enrolls, signs in/out, and reaches only the private Workspace | MFA, sessions, recovery, Grant-scoped authorization | Auth/CSRF/recovery/session/Workspace security tests | M1, Phase 2 package/policy decisions |
| M3: Working Scene editor with immutable revisions | Owner creates, views, edits, saves, and reloads Scenes | Normalized full snapshots, current pointer/version, provenance, HTML editor | Domain + request + exact-content + accessibility tests | M2, Phases 3–4 foundations |
| M4: Safe concurrency and conflict recovery | Stale tabs show manual recovery without overwriting work | Dual preconditions and durable save idempotency | Multi-tab, duplicate, timeout-after-commit, conflict tests | M3 |
| M5: Durable jobs and idempotency | Owner can observe/cancel bounded background work | PostgreSQL Jobs/Attempts/leases/retries/quarantine | Crash/redelivery/cancel/restore fault tests | M4, Phase 5 evidence |
| M6: Search | Owner finds and opens current authorized Scenes | Rebuildable current projections and asynchronous indexing | Workspace, stale-index, rebuild, restore, privacy tests | M5 and Scene domain |
| M7: Verified backup and restore | Owner can export and trust a tested recovery path | Encrypted backup, structured archive, isolated verified activation | Successful representative restore report and rollback exercise | M6, all authoritative schemas to date |
| M8: Legacy import | Owner dry-runs, reviews, and imports supported legacy material | Staging, new UUID mappings, atomic apply, provenance | Hostile-source, mapping, idempotency, all-or-nothing, recovery tests | M5, M7 |
| M9: AI suggestion workflow | Owner requests/reviews/applies one bounded Scene suggestion | Provider-neutral Job, context manifest, Suggestion, stale apply checks | Scope/privacy/provider-failure/stale/approval tests | M5–M7; provider decisions |
| M10: Production readiness | Owner securely uses and can recover the deployed workspace | Immutable release, roles, telemetry, runbooks, backup/restore, rollback | Production-readiness review, smoke, incident, restore, rollback evidence | M1–M9 and remaining Version 1 scope |

## Definition of Done

A phase or feature is done only when all applicable conditions hold:

- **Functionality:** acceptance criteria and failure states work end to end; status is truthful.
- **Authorization:** every private read/write reauthenticates as required, resolves actor/Workspace, and denies cross-Workspace access.
- **Privacy:** private text/secrets are absent from prohibited URLs, caches, logs, metrics, traces, Jobs, errors, and archives.
- **Migrations:** schema changes are reviewed, deterministic, tested from supported states, constraint-complete, and recovery-aware.
- **Tests:** unit, PostgreSQL integration, HTTP, worker, fault, security, and end-to-end evidence is proportionate and passing.
- **Accessibility:** baseline HTML and enhancements support keyboard use, labeled errors, focus, zoom, and announced status.
- **Observability:** bounded logs/metrics/events identify success and failure without disclosing content or creating high-cardinality labels.
- **Recovery:** authoritative state is included in backup/archive scope; restoration/reconciliation behavior is tested before production dependence.
- **Documentation:** user behavior, implementation interfaces, operations, security assumptions, and accepted residual risk are current.
- **Rollback/failure:** code/schema compatibility, partial failure, retry/idempotency, cancellation, and rollback or forward-recovery behavior are explicit and tested.

## Risks and Sequencing Constraints

| Risk or constraint | Consequence | Control |
| --- | --- | --- |
| Default Django user migrated before custom Account | Costly/unsafe identity replacement | Hard Phase 1 gate before first migration |
| Infrastructure-first delivery delays usable feedback | Architecture may drift from real writing needs | First vertical Scene slice by Phases 3–4 |
| Workspace authorization added after features | Cross-Workspace exposure and pervasive rework | Complete Phase 2 before private content UI |
| Autosave precedes concurrency/idempotency | Lost work or revision duplication | Defer autosave until Phases 3, 4, and 6 semantics exist |
| Jobs implemented separately per subsystem | Inconsistent retries/authority/recovery | Phase 6 common runtime before search/import/AI execution |
| Search becomes a second source of truth | Stale/unauthorized results | Source-version checks and full rebuild in Phase 7 |
| Destructive migration or launch before restore proof | Irrecoverable loss | M7 hard gate |
| Legacy import drives core identity/schema | Old assumptions contaminate new authority | New UUID mappings after core domain/recovery |
| AI integrated before staging/approval | Unreviewed provider output changes content | Phase 10 after Jobs and ordinary mutation rules |
| Product scope exceeds accepted schemas | Silent architecture invention | New ADRs/roadmap refinement for Characters/Locations/Links/hierarchy |
| Single-owner operational overload | Controls may be skipped | Small phases, concise automation/runbooks, explicit readiness review |

## Open Implementation Decisions

Only details deliberately left open by accepted ADRs are listed. “Resolve by” is the latest safe phase.

| Open decision | Resolve by |
| --- | --- |
| Supported Python and Django versions | Before Phase 0 completion |
| Package/dependency/build tooling and reproducible lock strategy | Phase 0 |
| Exact PostgreSQL version and local/test provisioning | Before Phase 1 |
| UUIDv7 implementation and UUIDv4 fallback library choice | Phase 1 |
| Django project and app/module layout | Phase 0 |
| Exact migration decomposition, constraint operations, and deferrability | Phase 1 |
| Initial numeric constants, sparse-order gap/rebalance, lifecycle labels | Phase 3 |
| Unicode normalization form, line endings, content limits | Phase 3 |
| Exact Account/login identifiers and authentication packages | Phase 2 |
| WebAuthn and TOTP libraries/policies | Phase 2 |
| Password/session/cookie/recent-auth policy values | Phase 2 |
| Bootstrap and emergency-recovery mechanisms | Phase 2 |
| Save fingerprint canonicalization and idempotency retention | Phase 4 |
| Editor enhancement/partial-page approach and diff interface | After M4, before autosave enhancement |
| Autosave timing, coalescing, and revision-churn policy | After Phase 6, before autosave |
| Browser-draft persistence and retention | Optional after M4 |
| Security Event/log schemas and retention | Phase 5 |
| Worker polling/claim strategy, leases, heartbeats, retry/backoff, concurrency | Phase 6 |
| Job/idempotency/attempt retention periods | Phase 6 |
| PostgreSQL search configuration, tokenization, ranking, snippets, indexes | Phase 7 |
| Search freshness targets and rebuild scheduling | Phase 7 |
| Backup tooling, archive serialization/container, encryption/hash/signature choices | Phase 8 |
| Backup schedules, retention, RPO/RTO, restore-test frequency | Phase 8 before M7 |
| Supported Story Engine formats/parser isolation/mappings/import limits | Phase 9 |
| Import artifact/staging retention | Phase 9 |
| AI provider, model, SDK, template/output schema | Phase 10 |
| AI cost/rate/context/output and retention limits | Phase 10 |
| Deployment platform, topology, TLS/reverse proxy/process supervisor | Phase 11 |
| Secret manager and encryption-key custody | Phase 11, with local interfaces in Phase 0 |
| Telemetry stack, alert channels/thresholds, retention | Phase 11 |
| Exact production resource/connection/request/worker limits | Phase 11 |
| Character, Location, Link/backlink, hierarchy, and content-state schemas/interactions | Before claiming final Version 1 product scope/M10 |

## First Implementation Slice

The recommended first working slice is deliberately narrow and ends with a usable, testable Scene workflow:

1. Initialize the Django project using the Phase 0 layout and supported versions.
2. Add validated local configuration with safe failure behavior.
3. Connect to local/test PostgreSQL; do not use a substitute database for integration tests.
4. Define the custom Account model before creating or running the first migration.
5. Add Workspace, owner Grant, and protected one-owner bootstrap sufficient for local authenticated use.
6. Implement Workspace-scoped Scene creation with a server-generated UUID and initial empty Revision.
7. Implement immutable initial and subsequent complete normalized Scene Revisions, current pointer, Scene version, and atomic save service.
8. Add a server-rendered authenticated Scene list and plain-text editor load page.
9. Add explicit complete-content POST save with expected Revision ID, expected Scene version, CSRF, authorization, validation, and idempotency.
10. Return a manual conflict response preserving the submitted draft and showing authorized current content; do not merge automatically.
11. Record Mutation Operation provenance for Scene creation and accepted saves.
12. Add focused automated tests for migrations, constraints, Workspace isolation, CSRF, exact content, immutable history, atomic saves, stale conflicts, duplicate delivery, safe rendering, privacy, and keyboard-accessible forms/status.

This slice intentionally excludes autosave, AI, search, legacy import, general background workers, full MFA, backup automation, and production deployment except for minimal interfaces that prevent later architectural rework. Before real private content or production use, the later authentication, MFA, recovery, backup, restore, and operational phases remain mandatory.

