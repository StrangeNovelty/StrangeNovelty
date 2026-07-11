# ADR-0014: Deployment Environments, Secrets, Operations, and Observability

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 boundaries for isolated deployment environments, validated configuration, secret and encryption-key custody, service identities and process roles, database privileges, immutable release identity, explicit migrations, health and readiness, privacy-minimized logs, bounded metrics and optional tracing, Security Events, alerts, operational and break-glass access, maintenance, incidents, backup and restore operations, Job operations, resource limits, dependency management, compatibility-aware rollback, release verification, and runbooks, while exact Python, Django, PostgreSQL and package versions, hosting topology, operating system, domain and TLS termination, reverse proxy, process supervisor, container runtime and registry, cloud region, configuration schema and injection mechanism, secret manager and key-custody mechanism, database role decomposition and grants, artifact signing and vulnerability scanning, health routes, resource and connection limits, migration operations, log/metric/trace schemas and vendors, retention periods, alert thresholds and channels, maintenance interface, incident criteria, backup tooling, deployment automation, and runbook procedures remain undecided.

## Decision Owners

- Decision owner: repository owner
- Author: Codex, acting as architecture-drafting assistant
- Reviewers: repository owner; implementation, security, privacy, database, and operations reviewers when assigned

## Context

Strange Novelty is documentation-only, but its accepted architecture now defines a private Django modular monolith, PostgreSQL authority, distinct web and worker roles, durable database-backed Jobs, protected backup and restoration, bounded AI, rebuildable search, and staged import. Before implementation, the repository needs an operational boundary that explains how those components may be configured, deployed, observed, recovered, and administered without weakening privacy or authorial control.

The primary operator and owner may initially be one person. That reduces staffing, not risk: account compromise, an over-privileged credential, a failed migration, an unverified backup, or private text in telemetry could expose or destroy the complete archive. Version 1 therefore needs maintainable controls that do not assume enterprise infrastructure but preserve separation, least privilege, recoverability, and useful evidence.

This ADR does not select hosting, vendors, exact versions, topology, or tooling. It defines the invariants those later choices must satisfy. Application implementation remains unauthorized while this ADR is drafted.

## Decision

If accepted, Version 1 will use the following operational architecture.

1. Maintain isolated local-development, test, and production environments. Staging may be added later but is not required initially.
2. Production uses production-only data, databases, storage, credentials, secrets, encryption keys, and provider identities. Development and test use synthetic or deliberately sanitized data and never receive production secrets by default.
3. Load environment-specific configuration through a deployment-appropriate injection boundary, validate it against a versioned configuration schema at startup, and fail closed in production when required or unsafe settings are missing or invalid.
4. Keep secrets and key material outside Git, browser-delivered configuration, client code, Job payloads, logs, metrics, traces, portable archives, and author-facing exports. Use external secret injection appropriate to the eventual platform.
5. Separate application secrets, database credentials, provider credentials, signing keys, encryption keys, backup credentials, and recovery credentials by purpose. Store only bounded key identifiers and rotation metadata with application state; keep encryption keys separately from encrypted data and backups.
6. Use service identities distinct from human Accounts. Service identities do not become Workspace members, Canon authorities, or owner substitutes.
7. Run web and worker processes from the same immutable or content-addressed application release but as distinct runtime roles. Neither runs as operating-system root.
8. Treat migrations as one serialized, privileged operational action per release. Web and worker startup never implicitly runs migrations.
9. Use least-privileged PostgreSQL roles appropriate to migration, runtime web access, worker access, backup, restore, and read-only inspection. Exact decomposition may be refined, but routine production operation never uses a universal database superuser.
10. Identify every release by source commit, build identity, configuration-schema version, and expected migration state. Dependencies and images are pinned or reproducibly resolved; floating production images are prohibited.
11. Startup validates configuration and local prerequisites without mutating authoritative data. Liveness reports process survival; readiness reports whether the assigned role can safely serve. Checks are bounded and privacy-safe.
12. Optional AI or integration outages do not make core web service unready. Database or mandatory policy-boundary failure does.
13. Use structured, privacy-minimized operational logs with bounded event type, severity, timestamp, service role, release identity, and privacy-safe correlation identifier. Private content and secrets are excluded.
14. Use bounded-cardinality operational metrics. UUIDs, private identifiers, titles, raw errors, queries, filenames, IPs, and user agents are not metric labels.
15. Tracing is optional in Version 1. If introduced, it follows the same privacy, access, retention, redaction, and cardinality rules as logs and never replaces Job Attempt evidence.
16. Keep operational logs, Security Events, Mutation Operations, and Job Attempts separate. Each serves operations, security accountability, domain provenance, and execution evidence respectively.
17. Production errors shown to clients are generic and correlation-safe. Protected diagnostic records retain only redacted, bounded detail.
18. Alert on bounded operational and security symptoms: availability, elevated failures, database capacity/connectivity, failed migrations, backup or restore-verification failure, Job backlog/stuck leases, authentication/MFA anomalies, configuration/secret failures, and storage exhaustion. Exact thresholds and channels remain later work.
19. Production access is authenticated, least-privileged, attributable, and auditable. Prefer application and documented operational interfaces. Direct writes and shell/database break glass are exceptional, time-bounded, reviewed, and recorded.
20. Maintenance mode blocks new ordinary mutations while allowing narrowly authorized diagnostics, backup, restoration, migration, and recovery. It is distinct from an outage.
21. Incident response includes containment, service/credential isolation, secret rotation, session revocation, evidence preservation, owner-notification criteria, recovery verification, controlled return to service, and post-incident review.
22. Backup and restoration operations follow ADR-0009. A written backup is not dependable until monitored and restoration-tested; restoration occurs in an isolated non-serving environment before verified activation.
23. After restoration, unfinished Jobs, AI work, indexing, and imports remain quarantined until ADR-specific reconciliation. Operational tooling cannot bypass that boundary.
24. Deploy schema and code under an explicit compatibility plan. Prefer expand-and-contract migration when releases overlap. Destructive or long-running changes require backup, verification, capacity, lock, recovery, and rollback planning.
25. Application rollback is permitted only to a release compatible with the active schema. Database rollback and code rollback are separate decisions; irreversible migrations are not assumed reversible.
26. Bound requests, uploads, Job payloads, worker concurrency, database connections, provider calls, memory, disk, execution time, and telemetry volume. Exhaustion fails visibly without corrupting authoritative state.
27. Verify releases through configuration and migration checks, web and worker readiness, database connectivity, safe Job claiming, backup monitoring, and critical owner workflows using synthetic or privacy-safe evidence.
28. Before production use, maintain reviewed runbooks for deployment, migrations, backup, verified restore, secret/key rotation, maintenance, incidents, break glass, rollback, and recovery.

## Terminology and Boundaries

- An **environment** is an isolated runtime/configuration/data boundary; it is not a Workspace.
- **Configuration** controls behavior and may be non-secret; a **secret** grants access or proves identity.
- An **encryption key** transforms/protects data; a key identifier is non-secret lookup metadata and not the key.
- An **Account** is a human identity. A **service identity** authorizes one bounded process role.
- The **web role** serves HTTP and enforces request policy. The **worker role** claims and executes Jobs.
- The **migration role** may change schema; runtime roles should not inherit that authority.
- **Startup** initializes a process. **Liveness** reports survival. **Readiness** reports safe availability for its assigned role.
- A health response is a bounded signal, not an operational inventory.
- An **operational log** supports diagnosis; a **Security Event** records security-relevant facts; a **Mutation Operation** records creative provenance; a **Job Attempt** records execution.
- A trace connects bounded spans; it is not authoritative evidence. A metric aggregates bounded measurements; it is not an audit record.
- A correlation ID connects evidence and grants no authority.
- An alert is a detection signal. An incident is a managed response to potential harm.
- Maintenance mode is an intentional restricted state, not merely unavailability.
- A release is an application artifact/configuration expectation. A migration changes schema/data shape.
- Deployment rollback changes application release; database rollback changes data/schema and may be impossible.
- Restore loads and validates state; activation makes verified restored state serve users.
- Operator capability does not imply owner authorization or creative authority.
- A resource limit protects capacity; it is not a creative business rule.
- Observability is bounded evidence for operation, not permission to disclose private data.

## Environment Model

Version 1 defines local development, automated/manual test, and production. Their databases, storage namespaces, credentials, secret sets, encryption keys, provider accounts, and telemetry destinations are isolated. Environment labels cannot substitute for authorization checks.

Production data is never routinely copied to developer machines. Any exceptional diagnostic copy requires an explicit sanitized procedure, authorization, inventory, retention, and deletion verification. Tests use synthetic data. A later staging environment must be independently isolated and may not become a quiet production mirror.

## Configuration Model

Configuration is injected at deployment and validated before readiness. A versioned configuration contract identifies required, optional, mutually exclusive, and production-prohibited values. Production-safe defaults are conservative; ambiguous security settings fail closed.

Configuration values are not all secrets, but all are treated as untrusted input until parsed, bounded, and validated. Startup reports safe categories of errors, never values. Configuration changes receive release/change evidence and rollback planning proportional to impact.

## Secret and Key Management

Secrets enter processes through a platform-appropriate external injection mechanism. No specific environment-variable, mounted-file, agent, or API mechanism is selected; implementations must address process listings, filesystem permissions, crash reports, child-process inheritance, and rotation.

Secrets are purpose-scoped, least-privileged, rotatable, and separately recoverable. Encryption keys are kept apart from ciphertext and backups. Key identifiers, states, creation/rotation dates, and algorithm/version references may be recorded without key material. Lost keys are a recovery risk requiring documented custody and rotation procedures.

## Service Identities and Process Roles

Web, worker, migration, backup, restore, and inspection actions use attributable bounded identities. A service identity cannot log in as the owner, approve AI/import content, mark Canon, or become a Workspace Grant. Jobs still reauthorize Workspace and operation preconditions.

Web accepts requests and coordinates short transactions. Workers execute ADR-0010 Jobs. Migration and recovery tooling are invoked separately. Operating-system users, database roles, and provider credentials should align with these responsibilities without requiring one process per logical module.

## Database Roles and Privilege Boundaries

Production distinguishes schema-changing authority from ordinary runtime authority. Migration credentials are unavailable to routine web/worker processes. Backup credentials can read what the selected backup mechanism requires but cannot serve ordinary application traffic. Restore authority targets isolated recovery environments and does not imply activation authority. Read-only inspection is bounded and audited.

Exact grants depend on PostgreSQL and deployment tooling. Django authorization remains mandatory even when database roles restrict capability. Database superuser access is break glass only.

## Deployment Artifact and Release Identity

A release is immutable after build and identifies source commit, build identity, dependency resolution, configuration schema, and compatible migration range. The same artifact is promoted rather than rebuilt with hidden differences where practical. Private data and secrets are never baked into artifacts.

Supply-chain evidence should support dependency review, reproducible resolution, provenance, vulnerability response, and rollback. Exact image, signing, registry, and scanning systems remain undecided.

## Startup, Liveness, and Readiness

Startup validates configuration, release compatibility, required filesystem permissions, and bounded dependency reachability without migrations or domain writes. Liveness is cheap and process-local. Readiness is role-specific: web requires its policy/database/session prerequisites; workers require safe database access and Job-claim capability.

Health responses reveal only broad state and safe reason categories. They exclude stack traces, topology, database contents, versions useful to attackers, private IDs, and credentials. Optional-provider degradation is surfaced operationally without disabling core writing.

## Web and Worker Deployment

Web and worker roles share code and release identity but scale, restart, and report readiness independently. Graceful shutdown stops new requests/claims, bounds drain time, and preserves/relinquishes Job leases safely. Neither role assumes local disk is durable authoritative storage unless later decided.

Worker concurrency and web/database pools are bounded together to avoid exhausting PostgreSQL. A worker restart relies on leases and idempotency, not process memory.

## Migration Execution

Migrations are reviewed release artifacts executed once by a separately authorized operator or deployment action. Execution is serialized, observable, and fails visibly. The migration plan includes prerequisites, expected locks/duration, backup state, compatibility window, verification, and recovery.

Data migrations are bounded and restart/recovery-aware. Long-running transformations may require later Jobs or staged releases; they must not be hidden inside routine startup. Secrets and owner passwords never appear in migrations.

## Release Compatibility and Rollback

Every release declares which schema states it can safely run against. Expand-and-contract changes allow compatible overlap when needed: add/backfill/read compatibility before removing old shape. Destructive changes wait until rollback and old readers are no longer required.

Rolling back code does not revert committed domain mutations or schema. Before rollback, verify schema compatibility, Job compatibility, external effects, and configuration. Database rollback normally uses a tested recovery plan or forward repair, not casual reversal.

## Logging

Logs are structured and privacy-minimized. Permitted fields include bounded event code, severity, time, service/release role, safe duration/status buckets, and a privacy-safe correlation ID. Necessary stable IDs may appear only in protected, access-controlled logs with documented purpose and retention; they never grant authority.

Never log manuscript bodies, private titles, prompts/responses, search queries/snippets, import bodies/paths/filenames, passwords, cookies, sessions, MFA/recovery material, authorization headers, database strings, provider tokens, encryption keys, exports, or backups. Redaction occurs before emission, including exception handling.

## Metrics

Metrics aggregate bounded operational facts: request/job counts, latency buckets, error classes, queue depth, lease age, connection/capacity status, backup age/result, and restore-test outcome. Labels use fixed vocabularies such as role, environment class, release, operation class, and bounded outcome.

Private or high-cardinality values are prohibited as labels. Metrics cannot answer manuscript or user-behavior questions unless a later privacy decision authorizes bounded analytics.

## Tracing and Correlation

Tracing is optional, sampled/bounded, and disabled or minimized where safe redaction cannot be guaranteed. Spans contain operation classes and safe timing, not inputs, SQL values, URLs with private parameters, provider bodies, or Job payloads.

Correlation identifiers are random/non-semantic, bounded in retention, and propagated only across trusted boundaries as needed. They link logs, Security Events, Job Attempts, and provider-effect evidence without collapsing those records.

## Security Events and Auditability

Security Events record bounded authentication, authorization, account/MFA/recovery, secret/configuration, administrative, break-glass, restore-activation, and suspicious-rate outcomes. They identify actor/service category, event type, target class and bounded reference where necessary, outcome, time, and correlation evidence.

They exclude manuscript content and do not replace creative provenance. Access, integrity, retention, and review are stricter than ordinary logs. Database administrators cannot silently rewrite authorial history merely because operational evidence exists.

## Error Handling

Client errors are generic, actionable where safe, and resist record/account enumeration. A correlation value may support owner troubleshooting. Internal errors are classified, redacted, and retained in protected systems for bounded periods.

Error handling must not turn a provider outage into authoritative corruption, expose configuration, or retry permanent failures indefinitely. Resource exhaustion rejects or delays work safely.

## Alerts and Operational Detection

Alerts derive from bounded metrics/events and cover service unavailability, elevated errors, database capacity/connectivity, failed migrations, backup failure/staleness, restore-verification failure, Job backlog/stuck leases, authentication/MFA anomalies, secret/configuration failures, and storage exhaustion.

Thresholds, escalation timing, and notification channels are later operational decisions. Alerts contain safe summaries and links to protected evidence, not private content.

## Operational Access and Break Glass

Routine operation uses authenticated application and documented interfaces. Production shell, database, backup, and secret access are narrowly granted, attributable, and reviewed. Developer-machine production access is not routine.

Break glass requires a declared incident/repair purpose, recent strong authentication, time-bounded credentials, least scope, preserved evidence, independent/owner review where feasible, session/secret rotation where implicated, and reconciliation through application invariants. Direct writes are exceptional and never silently create Canon or approval.

## Maintenance Mode

Maintenance mode rejects or pauses new ordinary mutations and Job claims while allowing safe reads if consistent, owner authentication, bounded diagnostics, migrations, backup, restoration, and recovery actions. Existing in-flight work reaches safe checkpoints or is quarantined.

The mode and reason are observable without exposing topology or private details. Activation and exit are attributable operational actions with readiness verification.

## Incident Response

The incident lifecycle is detect, assess, contain, preserve evidence, eradicate, recover, verify, notify under documented criteria, and review. Procedures cover credential compromise, data exposure, unauthorized mutation, database/storage failure, malicious import, provider compromise, and supply-chain incidents.

Recovery includes secret rotation, session revocation, Job/effect reconciliation, backup/restore verification, Workspace isolation checks, and post-recovery monitoring. This ADR claims no legal or regulatory compliance.

## Backup and Restore Operations

ADR-0009 governs scope, encryption, generations, staging, validation, activation, and identity. Operations monitor backup completion and freshness, protect credentials separately, and conduct representative isolated restore tests. A backup job success flag alone is insufficient.

Activation requires verified results, explicit owner authorization/recent authentication, controlled cutover, pre-activation evidence, rollback path, session invalidation, and post-activation checks. Restored credentials and Jobs are not blindly trusted.

## Job and Worker Operations

Workers expose bounded queue depth, oldest-ready age, lease age, attempts, terminal/quarantine counts, and safe error classes. Operators may pause claims, drain workers, quarantine, reconcile, or authorize manual retry under ADR-0010.

Operational restart never resets idempotency, attempt history, ambiguous provider state, or cancellation evidence. Job payloads remain private and minimized.

## Resource Limits and Capacity

Documented limits cover HTTP size/time, uploads, connections, transactions, Job payloads, concurrency, provider calls, memory, CPU, disk, telemetry, and backup workspace. Exact values follow measurement and synthetic testing.

Capacity signals warn before exhaustion. Load shedding preserves authentication, recovery, and authoritative integrity. Limits do not silently truncate content or partially commit mutations.

## Dependency and Image Management

Dependencies use supported versions and pinned/reproducible resolution. Updates are reviewed for security, compatibility, migrations, privacy, and rollback; release notes record material changes. Floating `latest` artifacts are not production identities.

Vulnerability and provenance scanning may be adopted later. A scanner result is evidence, not proof of safety, and must not upload private source or secrets to an unauthorized service.

## Release Verification

Before activation verify artifact identity, configuration schema, secret availability without disclosure, migration state, web/worker readiness, database connectivity, Job claiming/lease behavior, backup monitoring, and privacy-safe critical owner workflows. After activation verify errors, capacity, queues, and security events.

Verification uses synthetic records or bounded assertions and never prints manuscript content. Failure blocks or rolls back activation when safe.

## Operational Documentation

Production readiness requires version-controlled, non-secret runbooks for deployment, migrations, rollback, maintenance, backup, isolated restore/activation, secret/key rotation, incident response, break glass, Job reconciliation, and dependency updates.

Runbooks name prerequisites, authority, safe evidence, failure points, verification, escalation, and review cadence. Secret values and production topology details that increase risk live in separately protected operational material.

## Privacy and Data Handling

Production private data stays inside its authorized environment and approved backup/provider boundaries. Non-production uses synthetic or explicitly sanitized data. Telemetry minimizes collection, access, transmission, and retention.

IP addresses and user agents are sensitive operational metadata with bounded retention. Observability providers, if selected, are external processors requiring a later data-flow and secret review. Filenames, object keys, URLs, and alert messages use safe generated values.

## Django Application Boundary

Django owns HTTP/session/CSRF enforcement, server-side authorization, safe error rendering, configuration integration, Security Event creation, bounded logging, health views, maintenance enforcement, and application system checks. It does not become a secret manager, deployment orchestrator, or database superuser.

Django startup checks validate but do not mutate schema or data. Web and worker entry points use explicit role configuration. Exact settings modules, middleware, handlers, logging configuration, checks, and health routes remain implementation work.

## PostgreSQL Boundary

PostgreSQL remains authoritative for structured state, Jobs, idempotency, security evidence, and migration history. Roles and grants constrain operational capability; transactions and constraints protect integrity. PostgreSQL is not a general secret store or observability sink.

Connections require protected credentials and deployment-appropriate transport. Pooling, TLS topology, role names, connection limits, statement/lock timeouts, monitoring queries, replication, and high availability remain undecided.

## Rationale

This model gives one owner a small but defensible operational architecture. Environment isolation and secret separation reduce catastrophic cross-contamination. Explicit roles and migration execution prevent routine processes from accumulating schema or superuser authority. Privacy-minimized observability makes failures diagnosable without creating another manuscript store. Compatibility-aware releases, verified restoration, and reconciliation protect the archive through deployment and disaster recovery.

It preserves provider and hosting portability because it specifies properties rather than products. It also keeps optional integrations from controlling core availability and ensures operations cannot silently acquire creative authority.

## Decision Criteria

The selected approach is judged by:

1. privacy of unpublished creative work and credentials;
2. integrity of authoritative PostgreSQL state;
3. least privilege and attributable operational action;
4. recoverability proven through restoration;
5. maintainability for one owner;
6. failure isolation between web, workers, providers, and operations;
7. useful but bounded observability;
8. compatibility-aware migration and rollback;
9. reproducible, reviewable releases; and
10. portability across future hosting and tooling choices.

## Alternatives Considered

### One shared environment

Simpler initially, but unacceptable because tests and development could expose or mutate production data and secrets.

### Isolated development, test, and production

Selected. It provides the minimum meaningful separation. Mandatory staging is deferred because it adds cost for one owner; later staging must be isolated.

### Committed configuration and secrets

Rejected for secrets and environment-specific values. Non-secret configuration schemas and safe examples may be committed, but secret-bearing files may not.

### Environment variables only

Portable and simple, but may leak through process/debug tooling. Acceptable only as one platform injection mechanism with controls; not mandated.

### Platform injection or external secret storage

Selected boundary without vendor choice. It supports rotation and access control while preserving deployment flexibility.

### One universal service/database account

Rejected. It expands blast radius and makes attribution and rotation difficult.

### Separate service identities and database roles

Selected proportionally. Exact role count may be consolidated where evidence shows equivalent least privilege.

### Web processes run migrations automatically

Rejected because concurrent startup, excessive credentials, and invisible failure create operational ambiguity.

### Explicit one-time migration execution

Selected for serialization, observability, review, and privilege separation.

### Unstructured logs with raw errors

Easy to start, but rejected because redaction, aggregation, cardinality, and privacy are unreliable.

### Structured privacy-minimized logs and protected errors

Selected. Diagnostic depth is bounded by sensitivity and access.

### No metrics or tracing

No metrics would make backlog, capacity, and recovery failure hard to detect. Bounded metrics are selected; tracing remains optional.

### Full distributed tracing

Deferred. A modular monolith does not initially justify its privacy and operational cost.

### Operational logs as security audit

Rejected because retention, integrity, subject matter, and access needs differ. Security Events remain separate.

### Direct database administration and permanent shell access

Rejected as routine control planes. They remain time-bounded break glass only.

### Application and documented operational interfaces

Selected because they preserve authorization, validation, invariants, and attributable action.

### Backup-only recovery confidence

Rejected. ADR-0009 requires isolated verified restoration.

### Automatic resumption after restore

Rejected. Unfinished work is quarantined and reconciled to avoid duplicate external effects.

### In-place mutable deployments and floating versions

Rejected because release identity, rollback, and incident diagnosis become unreliable.

### Immutable releases and reproducible versions

Selected, with exact artifact/signing technology deferred.

### Roll back application regardless of schema

Rejected. Only compatibility-aware rollback is safe.

### No maintenance mode

Rejected because recovery and migrations need an explicit restricted state distinct from uncontrolled outage.

### Undocumented incident handling

Rejected. The single-owner context makes concise tested runbooks more important, not less.

### Production data in development

Rejected by default. Use synthetic or explicitly sanitized data under a protected exceptional procedure.

## Comparative Assessment

### Environment strategy

| Strategy | Isolation | Cost | Decision |
| --- | --- | --- | --- |
| One shared environment | Poor | Low | Reject |
| Dev/test/production isolation | Strong minimum | Moderate | Select |
| Mandatory staging | Stronger rehearsal | Higher | Defer |

### Secret-management strategy

| Strategy | Rotation/control | Exposure risk | Decision |
| --- | --- | --- | --- |
| Git/config database | Poor | Critical | Reject |
| Environment variables only | Platform-dependent | Moderate | Permit, not mandate |
| External platform injection/storage | Strong | Lower | Select boundary |

### Service and database identity strategy

| Strategy | Least privilege | Operability | Decision |
| --- | --- | --- | --- |
| Universal superuser | None | Superficially simple | Reject |
| Purpose-bounded identities/roles | Strong | More setup | Select |

### Migration execution strategy

| Strategy | Concurrency safety | Privilege | Decision |
| --- | --- | --- | --- |
| Every web/worker startup | Poor | Excessive | Reject |
| Serialized release action | Strong | Bounded | Select |

### Logging strategy

| Strategy | Diagnostic value | Privacy | Decision |
| --- | --- | --- | --- |
| Raw/unstructured | Inconsistent | Poor | Reject |
| Structured and minimized | Strong bounded | Stronger | Select |

### Metrics and tracing strategy

| Strategy | Visibility | Cost/privacy | Decision |
| --- | --- | --- | --- |
| None | Poor | Low | Reject for metrics |
| Bounded metrics, optional tracing | Proportionate | Moderate | Select |
| Full tracing by default | High | High | Defer |

### Security audit strategy

| Strategy | Integrity/meaning | Decision |
| --- | --- | --- |
| Reuse operational logs | Ambiguous | Reject |
| Separate Security Events | Explicit | Select |

### Operational access strategy

| Strategy | Invariant preservation | Decision |
| --- | --- | --- |
| Permanent shell/direct writes | Poor | Reject |
| Interfaces plus bounded break glass | Stronger | Select |

### Deployment and rollback strategy

| Strategy | Reproducibility | Schema safety | Decision |
| --- | --- | --- | --- |
| Mutable/floating deployment | Poor | Poor | Reject |
| Immutable release, compatibility-aware rollback | Strong | Strong | Select |

### Restore-time operational behavior

| Strategy | External-effect safety | Decision |
| --- | --- | --- |
| Resume all work | Poor | Reject |
| Quarantine, reconcile, verify, activate | Strong | Select |

## Evidence

### Repository evidence

- `README.md` defines a documentation-only private workspace and prohibits committed private data.
- Product vision, principles, scope, and roadmap prioritize authorial control, privacy, a narrow Version 1, portability, backup, restoration, and maintainability for one owner.
- Architecture overview, security, data-model, AI-context, and integrations documents establish server authority, privacy-minimized logging, bounded providers, and recoverability.
- ADR-0001 through ADR-0013 establish the Django/PostgreSQL modular monolith, identity/revisions, authentication, schema, backup/restore, Jobs, AI, search, and import invariants preserved here.
- The architecture handoff records that implementation remains deferred pending prerequisites.
- The Story Engine audit identifies unsafe lessons to avoid: client-side authority, unrestricted local settings/credentials, environment-specific startup, incomplete logging/recovery boundaries, and broad coupled responsibilities.

### Official guidance reviewed conceptually

- Django deployment/system-check, settings, security, logging, and error-handling guidance supports production checks, protected settings, safe errors, and explicit deployment review.
- PostgreSQL role/privilege, connection, transaction, backup, and restore guidance supports least privilege, role separation, serialized schema work, and verified recovery.
- OWASP guidance on secrets, logging, authorization, secure configuration, errors, denial of service, incident response, and supply chains supports minimization, redaction, bounded access, response planning, and reproducible dependencies.
- Established operational practice supports immutable release identity, distinct liveness/readiness, bounded telemetry, graceful role shutdown, and restore testing.

This ADR deliberately avoids version-specific or vendor-specific claims. Exact implementation must recheck then-current official guidance.

## Consequences

### Positive

- Production secrets and manuscript data are isolated from ordinary development.
- Role separation limits compromise and accidental schema changes.
- Privacy-safe evidence improves diagnosis without creating a second manuscript repository.
- Releases, migrations, rollback, backup, and restore become reviewable operations.
- Provider and hosting choices remain portable.

### Negative

- Separate identities, releases, telemetry, and runbooks increase setup and maintenance.
- Strict redaction can reduce diagnostic detail.
- Compatibility-aware migrations may require multiple releases.
- Restore testing and incident exercises consume time and storage.
- A single owner must maintain operational discipline across several roles.

### Neutral or Operational

- Exact products, thresholds, credentials, topology, and runbooks remain follow-up decisions.
- Staging is optional initially.
- Tracing is permitted but not required.
- Some database roles may be combined only after a documented least-privilege review.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Secret leakage through configuration or telemetry | External injection, validation, pre-emission redaction, access control, rotation, and tests |
| Over-privileged service or operator | Purpose roles, no routine superuser, time-bounded break glass, attribution, review |
| Migration causes outage or data loss | Serialized reviewed action, backup verification, compatibility plan, bounded locks, release checks |
| Observability misses private failure detail | Safe correlation, protected bounded diagnostics, synthetic reproduction, explicit escalation |
| Cardinality/cost explosion | Fixed labels, budgets, sampling, retention, capacity alerts |
| False readiness | Role-specific bounded dependency checks and critical-flow release verification |
| Rollback runs incompatible code | Declared schema compatibility and expand-and-contract sequencing |
| Restore repeats external effects | Quarantine, session invalidation, reconciliation, verified activation |
| Key loss makes backups unusable | Separate custody, tested recovery, rotation metadata, restore exercises |
| Single-owner operational overload | Minimal vendor-neutral controls, concise runbooks, automation only after review |

## Security and Privacy Review

This decision is security- and privacy-sensitive. Protected assets include manuscripts, account/session/MFA state, credentials, keys, backups, import artifacts, AI context, provider data, and operational evidence. Trust boundaries include browser-to-web, web/worker-to-PostgreSQL, service-to-provider, build-to-runtime, operator-to-production, and backup/restore activation.

Primary threats are cross-environment exposure, secret compromise, excessive service privilege, telemetry leakage, malicious dependency/artifact, denial of service, unauthorized production access, unsafe migration/rollback, and unverified recovery. The decision mitigates them through isolation, least privilege, immutable identity, validation, minimization, bounded observability, explicit operations, and recovery testing.

Residual risks remain: deployment platforms can expose secrets to privileged operators; redaction can fail; one owner can make correlated mistakes; key loss can make encrypted data unrecoverable; and vendor outages can affect optional functions. Implementation requires configuration/redaction tests, permission review, dependency scanning appropriate to the chosen tooling, incident exercises, and representative restore tests.

## Product and Architecture Alignment

The decision supports private-by-default operation, authorial authority, trustworthy status, portability, recovery, and Version 1 maintainability. It does not add public access, collaboration, autonomous AI, or a new authoritative provider.

It preserves ADR-0001 through ADR-0013: Django remains policy boundary; PostgreSQL remains authoritative; Jobs remain durable; revisions/provenance/security evidence stay distinct; AI/search/import remain bounded; restoration remains verified and controlled. No normative product or architecture amendment is required by acceptance.

## Migration and Portability

Vendor-neutral boundaries preserve movement between hosting, secret, telemetry, and artifact systems. Release/configuration identity, database migrations, encrypted backup custody, and runbooks must be exportable/documented without exporting secret values.

Moving environments requires a fresh trust bootstrap: inject new secrets, verify keys/backups, migrate/restore into isolation, validate roles and configuration, invalidate unsafe sessions/work, and activate deliberately. Environment cloning never silently clones authority.

## Follow-Up Work

Before production implementation or use:

1. select supported runtime/database versions and deployment topology through appropriate review;
2. select configuration and external secret-injection mechanisms;
3. define database/service roles and grants;
4. define release artifact, dependency pinning, and supply-chain verification;
5. set health checks, resource limits, pools, timeouts, and graceful shutdown behavior;
6. define structured log schema, redaction, metrics, optional tracing, retention, and access;
7. define Security Event schema/review and alert thresholds/channels;
8. write and exercise deployment, migration, rollback, maintenance, incident, break-glass, backup, restore, rotation, and Job-reconciliation runbooks;
9. test failure, capacity, secret rotation, incompatible rollback, and isolated restoration with synthetic data; and
10. update implementation references after code and operations are authorized.

## Implementation References

None. This ADR creates no settings, secrets, infrastructure, roles, migrations, code, monitoring, runbooks, or deployment resources.

## Supersession and Amendment History

- 2026-07-11: Proposed and accepted after owner-directed architecture review.
- Supersedes: —
- Superseded by: —
