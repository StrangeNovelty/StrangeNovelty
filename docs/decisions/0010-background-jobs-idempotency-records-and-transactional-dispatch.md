# ADR-0010: Background Jobs, Idempotency Records, and Transactional Dispatch

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 architecture boundaries for durable background jobs, transactional dispatch, idempotency, retries, leases, cancellation, external effects, ambiguous outcomes, status, retention, operator authority, Workspace scope, privacy, and recovery reconciliation, while exact Python, Django, PostgreSQL, queue library, broker, scheduler, polling and claim strategy, worker count, lease and heartbeat durations, retry budgets and backoff constants, retention periods, payload schemas, fingerprint canonicalization, concurrency limits, provider-effect tables, indexes, database roles, and deployment configuration remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; Django, PostgreSQL, distributed-systems, security, privacy, authorization, AI, export, backup, restoration, and operations perspectives

## Context

Strange Novelty needs bounded asynchronous execution for work that should not block interactive requests or that requires controlled retry, progress, external providers, artifact creation, or recovery reconciliation. Likely examples include structured exports, database backup orchestration, restoration verification, imports, search rebuilds, and AI operations.

The system remains a modular monolith. Django application/query services are the policy boundary, PostgreSQL is authoritative, and one or more workers may run the same application codebase. A job runner is an execution environment, not a new source of domain authority.

ADR-0001 through ADR-0009 establish that the browser is untrusted; all private operations are authenticated, authorized, Workspace-scoped, and revalidated; stable UUIDs identify authoritative/supporting records; Scene revisions are immutable; external calls occur outside long database transactions; provider results remain non-authoritative; Mutation Operation records provenance; idempotency has distinct meaning; backups/restores quarantine unfinished work; restored sessions are invalidated; and external effects must be reconciled before resumption.

Queue delivery is not effect completion. A worker can crash after claiming, during an external call, after a provider succeeds, after a database commit, or before acknowledging delivery. Networks can time out without proving failure. PostgreSQL and an external provider cannot share one atomic transaction. Therefore the design must tolerate duplicate delivery and uncertain outcomes without claiming exactly-once execution.

The decision must distinguish:

- synchronous request handling from background execution and scheduled jobs;
- Job identity from domain identity;
- Job record from queue message;
- queue delivery from effect completion;
- at-least-once delivery from idempotent processing;
- exactly-once claims from practically idempotent effects;
- Job from domain command, domain event, Mutation Operation, Idempotency Record, Security Event, and provider operation;
- retry from duplicate redelivery and manual re-execution;
- cancellation request from completed cancellation;
- cancellation from rollback, compensation, and restoration;
- lease/lock/worker ownership from authorization and creative authority;
- progress from authoritative state;
- provider receipt from known provider success;
- timeout from known failure;
- ambiguous outcome from terminal failure;
- dispatch transaction from execution transaction;
- application transaction from external side effect;
- reconciliation from retry;
- terminal failure from restore-time quarantine;
- retention from archive or purge;
- operational-record deletion from domain-record deletion;
- restored pending work from safely resumable work;
- queue mechanism from job semantics;
- scheduler from worker;
- batch/workflow orchestration from event sourcing;
- correlation ID from secret;
- logs from durable evidence; and
- service identity from human Account identity.

Exact Python, Django, PostgreSQL, queue library, broker, scheduler, polling interval, worker count, lease duration, heartbeat, retry count, backoff constants, retention, batch size, concurrency, and deployment remain undecided.

## Decision

If accepted, Version 1 will use the following architecture.

1. Use PostgreSQL-backed durable Job, Job Attempt, Idempotency Record, and commit-coupled dispatch state before introducing an external broker.
2. Run one or more worker processes from the same modular-monolith codebase. Select no microservices platform or distributed workflow engine.
3. Treat delivery as at-least-once. Require idempotent handlers and idempotent/reconciled external-effect boundaries. Reject exactly-once claims across PostgreSQL and providers.
4. A Job row is the Version 1 durable dispatch/outbox record. Creating it in the same transaction as an authoritative change makes follow-up work visible only after commit and avoids a separate materialization gap.
5. A request whose primary purpose is asynchronous work creates the authorized operation/idempotency/job records in one short transaction, returns committed job identity/status, and does not publish to an external broker.
6. Workers poll committed available Job rows and claim them atomically with a bounded lease. Exact SQL and polling strategy remain later work.
7. Job records carry stable UUID, direct Workspace scope where private data is involved, constrained type/state, bounded reference payload, availability/time fields, attempt/retry information, lease fields, cancellation fields, advisory progress, initiator/service attribution, operation/idempotency references, target/result references, and bounded error classification.
8. Job payloads contain stable references and bounded non-secret parameters—not manuscript bodies, full prompts/responses, credentials, tokens, private titles, or large artifacts.
9. Record each execution in a narrow append-oriented Job Attempt table. Job carries summary/current state; attempts preserve start/end, worker/lease, outcome class, provider receipt references, and bounded errors.
10. Idempotency Records are durable PostgreSQL records scoped to Workspace, caller, operation, and key, with privacy-safe request fingerprint, state, result/operation reference, timestamps, and expiry. Reuse with different material input fails.
11. Idempotency never grants authorization. Expiry/cleanup never makes an unsafe repeated effect automatically safe.
12. Use a constrained Job state machine containing queued, available, running, retry-wait, cancellation-requested, succeeded, failed-terminal, cancelled, and quarantined concepts. Exact labels remain later work.
13. Claims use one active bounded lease with owner and expiry. Heartbeats may extend leases. Expired leases permit redelivery only because handlers revalidate and are idempotent/reconciling.
14. Retries use failure classification, bounded budgets, exponential backoff, and jitter. Permanent validation/authorization/precondition/version failures are terminal; transient infrastructure/provider failures may retry; ambiguous external outcomes require reconciliation before retry.
15. Cancellation is an authorized request and cooperative acknowledgement at safe checkpoints. It cannot undo committed domain or external effects automatically.
16. External calls occur outside long database transactions. Before the call, persist bounded intent/effect identity; after it, open a short transaction, revalidate current state, and conditionally record the result or authoritative mutation.
17. Provider idempotency keys are used when supported but do not prove exactly-once behavior. Persist bounded provider request/response/receipt identifiers and known-success, known-failure, or ambiguous status.
18. Authorization at enqueue time is necessary but insufficient. Workers re-resolve Workspace, Account/service authority, grant state, lifecycle, target identity/current version, and operation preconditions before every meaningful read, external effect, artifact publication, or domain commit.
19. Progress is advisory. Completed results reference authoritative records or protected artifacts rather than embedding large output.
20. Terminal/poison work remains failed-terminal or quarantined for bounded review. Manual retry is a new attributable execution decision requiring current authorization and, for high-impact operations, recent authentication.
21. After database/archive restoration, invalidate leases and quarantine unfinished jobs. Classify each as safe to regenerate, safe to retry, requires external reconciliation, terminal, or cancelled. Never blindly resume external effects.
22. Retain enough bounded Job/Attempt/Idempotency/effect evidence for reconciliation, recovery, security, and debugging without retaining sensitive payloads indefinitely. Cleanup is separate and cannot cascade to domain history, revisions, exports, or backups.
23. Queue, worker, and operator credentials are least-privileged. Worker/service identity is not a human Account or creative approval.

## Terminology and Boundaries

**Synchronous handling** completes bounded work inside an interactive request. **Background execution** runs durable work after the request. **Scheduled work** becomes eligible at a future time but follows the same Job semantics.

A **Job** is durable operational intent/state. A **queue message** is a delivery hint; Version 1 may have none outside PostgreSQL. A **domain command** asks application services to perform a domain operation. A **domain event** describes something that occurred. Neither is automatically a Job.

A **Mutation Operation** explains provenance for an authorized domain mutation. An **Idempotency Record** deduplicates a bounded request/effect. A **Security Event** records security-relevant evidence. They may reference each other but remain separate.

An **Attempt** is one worker execution. **Redelivery** is renewed delivery of the same Job. **Retry** is a policy decision after classified failure. **Manual retry** is a newly authorized execution decision.

A **lease** is temporary exclusive claim evidence, not permission. A **heartbeat** extends it. Worker ownership does not mean the worker is trusted indefinitely or owns the creative record.

**At-least-once delivery** means duplicate attempts are possible. **Idempotent processing** ensures repeated equivalent attempts converge on one intended durable effect. **Exactly-once effect** across independent systems cannot be assumed.

An **ambiguous external outcome** means the application cannot tell whether a provider performed an effect. **Reconciliation** asks provider/local evidence before another effect. A timeout is not proof of failure.

**Cancellation request** states intent to stop future safe work. **Cancellation acknowledgement** confirms the worker reached a checkpoint. Cancellation is not rollback, compensation, or restoration.

**Quarantine** prevents restored, ambiguous, unsafe, or poison work from executing until classified. **Terminal failure** is a completed policy conclusion. A dead-letter mechanism is an operational view/state, not a separate creative archive.

## Job Architecture Principles

- Keep authoritative job state in PostgreSQL.
- Use short transactions and no provider/network call inside a held application transaction.
- Couple dispatch durability to the authoritative commit.
- Expect crashes, redelivery, timeouts, deploy interruption, and duplicate claims.
- Revalidate authorization/current state at execution time.
- Make handlers idempotent or reconcile before effects.
- Minimize payloads and dereference current data through scoped services.
- Keep Job, Attempt, Idempotency, Mutation Operation, Security Event, and provider-effect meanings distinct.
- Use constrained states rather than contradictory booleans.
- Make progress/status honest but non-authoritative.
- Preserve bounded failure evidence without copying private inputs/outputs.
- Fail closed on unknown Workspace, revoked grant, lifecycle prohibition, stale target, unsupported version, or inaccessible record.
- Keep queue mechanics replaceable without changing stable Job identity or semantics.
- Prevent retry storms, queue flooding, starvation, and poison loops with later limits.

## Job Record

The durable Job record contains logically:

- stable application-generated UUID;
- optional direct Workspace foreign key, required for private Workspace work;
- constrained job type;
- constrained state;
- bounded priority only if justified;
- availability timestamp;
- created, started, and completed timestamps where applicable;
- bounded attempt count and retry-policy/maximum-attempt reference;
- current lease owner, lease expiry, and heartbeat time;
- cancellation-request and cancellation-completion/acknowledgement times;
- advisory progress phase and optional bounded percentage;
- non-secret correlation ID;
- initiating Account reference when applicable;
- bounded service identity/category;
- Mutation Operation reference where the job supports a domain operation;
- Idempotency Record reference where relevant;
- typed/bounded target references;
- protected artifact or authoritative result references;
- bounded error category/code and safe summary; and
- restore/quarantine classification metadata.

State, availability, attempt summary, lease, cancellation, terminal outcome, and result references are authoritative operational state. Progress percentage, phase text, estimated completion, and display messages are advisory.

Payload/reference fields contain IDs, versions, operation type, safe bounded options, and integrity/version metadata. They exclude manuscripts, private titles, full AI manifests/prompts/responses, raw imported documents, credentials, tokens, cookies, provider secrets, backup bodies, archive paths exposed to users, and unbounded exception data.

Job identity is not target identity, provider identity, authorization, or idempotency. A Job may be retried through attempts while remaining the same Job; a manual re-execution may create a new Job linked to the original depending on policy.

## Job Attempt Boundary

Version 1 uses a hybrid: current summary counters/timestamps on Job plus an append-oriented Job Attempt record for each claim/execution.

Attempt records contain:

- stable UUID;
- Job and Workspace scope through direct or constrained reference;
- monotonically allocated attempt number unique within Job;
- worker/service identity or bounded instance correlation;
- lease identity/claim time and expiry snapshot;
- execution start/end timestamps;
- outcome class: success, retryable, terminal, cancelled, lease-lost, shutdown, or ambiguous/reconciliation-required;
- bounded error category/code;
- external-effect/provider receipt references when relevant;
- retry decision/next-availability reference; and
- no private input/output bodies.

Attempts are append-oriented operational evidence. They do not become creative provenance or security events automatically. Job summary can be rebuilt/reconciled from attempts plus current state where necessary, but attempts are not an event-sourced queue.

Counters only would lose worker/outcome/reconciliation evidence. Logs only are too ephemeral, privacy-risky, and not authoritative. Full payload snapshots per attempt are rejected.

Exact attempt retention, worker identifier granularity, and lease snapshot fields remain later physical decisions.

## Idempotency Record

An Idempotency Record represents one bounded retriable operation under one caller/Workspace scope.

It contains logically:

- stable UUID;
- direct Workspace where applicable;
- operation type/version;
- Account/service caller scope;
- client-provided or trusted server-generated key;
- canonical privacy-safe request fingerprint;
- constrained state such as pending, committed, failed-known, or ambiguous;
- Job, Mutation Operation, authoritative result, or protected artifact reference;
- created, completion, last-seen, and expiry timestamps;
- bounded failure/reconciliation category; and
- replay behavior metadata sufficient to return/reconstruct the prior safe result.

The same scoped key and fingerprint returns or reconciles the prior result instead of duplicating it. The same key with a different fingerprint fails visibly. Cross-Workspace or cross-caller reuse fails.

Fingerprints derive from a canonical bounded operation description and stable content hash/reference where necessary. Manuscript bodies are not copied into idempotency rows. A hash is not an authorization token and may itself be sensitive metadata.

Idempotency Record is distinct from Mutation Operation: the former deduplicates requested effects; the latter explains a domain mutation's origin. A Mutation Operation may reference the Idempotency Record that protected it.

Cache-only idempotency is rejected because eviction/restart can permit unsafe replay. Durable PostgreSQL storage is selected. Expiry removes the replay guarantee; it cannot make a previously ambiguous non-idempotent effect safe to repeat. Cleanup must preserve references needed by committed Mutation Operations and reconciliation.

## Dispatch and Outbox Boundary

Version 1 uses the Job row as both durable job state and commit-coupled dispatch/outbox record.

### Domain transaction with follow-up work

The application performs the authoritative domain mutation and inserts the bounded Job row in the same PostgreSQL transaction. Before commit, workers cannot see the Job. On rollback, neither domain change nor Job exists. After commit, a polling worker can claim it without a broker-publish gap.

### Request whose purpose is asynchronous work

The service authenticates, authorizes, validates, fingerprints/idempotency-checks, creates Mutation Operation/Idempotency/Job records as applicable in one short transaction, commits, and returns job status. The work begins later.

A separate Outbox table is not required initially because PostgreSQL is itself the queue and the Job row already represents dispatch intent. The schema should remain outbox-compatible: a future relay may publish committed Job identity to an external broker without changing Job authority/state.

Direct broker publish before database commit is rejected because workers may execute rolled-back intent. Publish after commit without a durable row/callback-only is rejected because process failure can lose work between commit and publish. Post-commit callbacks may wake workers as an optimization, never as sole durability.

If a future broker requires delivery state distinct from Job execution, a separate Dispatch/Outbox record may be added through a later ADR. Broker messages carry Job ID/version only and do not become authoritative state.

## Job State Machine

Version 1 constrains current Job state around these semantics:

- **queued:** committed durable intent not yet eligible or fully prepared;
- **available:** eligible for claim now;
- **running:** actively leased to a worker;
- **retry-wait:** classified retryable and unavailable until a later time;
- **cancellation-requested:** owner/operator requested cancellation but completion is not acknowledged;
- **succeeded:** intended local job outcome completed and recorded;
- **failed-terminal:** cannot/should not retry automatically;
- **cancelled:** cooperative cancellation completed before further prohibited effects;
- **quarantined:** execution disabled pending restore/ambiguity/operator reconciliation.

Possible transitions include queued→available, available→running, running→succeeded, running→retry-wait, retry-wait→available, running→failed-terminal, queued/available/running→cancellation-requested, cancellation-requested→cancelled or succeeded/failed when too late, and unfinished restore states→quarantined.

`blocked`, `waiting-on-dependency`, `reconciling`, batch/child states, and workflow orchestration are later extensions. Version 1 can represent reconciliation need through quarantined/attempt/effect metadata without prematurely adding a workflow engine.

Terminal state does not mean the record is immediately deleted. State transitions occur through services/atomic claims and are protected against stale lease owners.

## Claiming, Leasing, and Heartbeats

A worker atomically selects an eligible available Job, verifies its state/availability, claims it, creates an Attempt, and records a unique lease owner/identity and expiry in a short transaction.

One active lease is permitted. Database locking or conditional update prevents ordinary double claim, but crashes and delayed workers still make duplicate attempts possible after expiry.

The lease:

- expires after a bounded duration selected later;
- may be extended through heartbeat for work making progress;
- is checked before sensitive checkpoints/commits;
- does not authorize Workspace access or external effects;
- can be invalidated by cancellation/quarantine/recovery; and
- cannot prove a worker is dead or prevent a partitioned worker from continuing external code.

An expired lease makes a Job eligible for recovery/redelivery only after state/effect classification. Idempotent handlers and external reconciliation make that safe; the lease alone does not.

Workers use database time or a documented consistent time source for availability/expiry comparisons. Clock skew, delayed heartbeats, deployment shutdown, long provider calls, and paused workers require synthetic testing.

Fairness, priority, starvation, polling batch size, `SKIP LOCKED` or equivalent claim syntax, advisory locks, lease duration, and heartbeat frequency remain later choices. Database transactions remain short; locks are never held for the entire job/provider call.

## Retry Classification and Backoff

Retries are policy decisions based on classified failures:

| Failure class | Default handling |
| --- | --- |
| Invalid/malformed input | Terminal |
| Authorization or revoked grant | Terminal; do not reveal target |
| Workspace mismatch | Terminal/security review category |
| Lifecycle/precondition failure | Terminal unless explicit later reauthorization creates new work |
| Stale Scene version/current pointer | Terminal conflict; never blind retry |
| Unsupported schema/content/archive version | Terminal/quarantine |
| Deterministic provider rejection | Terminal |
| Transient database connection | Retry within budget |
| Deadlock/serialization conflict | Short bounded retry with full revalidation |
| Network connection failure before confirmed send | Retry only when send state is known safe |
| Network timeout after possible send | Reconciliation required |
| Provider rate limit | Retry-wait using bounded provider-neutral policy |
| Provider 5xx/temporary outage | Retry within budget if effect is idempotent/reconcilable |
| Provider permanent rejection | Terminal |
| Storage temporarily unavailable | Retry within budget |
| Cancellation request | Cooperative cancellation path |
| Deployment shutdown/lease loss | Redelivery after safe classification |

Retry delays use bounded exponential backoff with jitter to avoid synchronized storms. Policies vary by job/effect class and respect rate/cost limits. Exact budgets/constants remain later operational decisions.

Unlimited retries are rejected. Attempt counts/failure evidence are not silently reset. A poison Job reaches failed-terminal or quarantined and requires review.

Manual retry is not an administrative button that bypasses policy. It reauthenticates/authorizes, rechecks effect ambiguity/current state, creates attributable evidence, and may create a new Job or new Attempt according to whether the original operation identity remains valid.

## Cancellation

Cancellation is an explicit authorized request recorded separately from completion.

For queued/available work, cancellation can transition safely to cancelled if no lease/effect began. For running work, the state becomes cancellation-requested and the worker checks at safe cooperative checkpoints.

Workers should check before:

- fetching sensitive content;
- constructing/sending an external request;
- publishing an artifact;
- committing an authoritative mutation;
- starting another batch item; and
- scheduling follow-up work.

If an external request has already been sent, cancellation does not prove the provider stopped. The attempt/effect becomes known/ambiguous and requires receipt/reconciliation. If an authoritative transaction already committed, cancellation cannot roll it back; reversal requires an ordinary domain operation, compensation, or restoration according to the relevant ADR.

Forced process termination is an emergency operational action, not cancellation semantics. It may leave an expired lease and ambiguous effects.

High-impact export, backup deletion, restore/activation, purge, or provider operations may require recent authentication to request cancellation/manual retry. Exact UI/transport is undecided.

Cleanup after cancellation removes transient files/context under protected rules without deleting authoritative records or evidence required for reconciliation.

## External Effects and Ambiguous Outcomes

Version 1 records bounded external-effect evidence as part of Job Attempt unless a later provider/integration ADR requires a separate Provider Operation table.

The bounded record includes:

- provider/service category and operation type;
- application effect/idempotency key;
- attempt and Job/Mutation Operation references;
- provider request/response/receipt IDs where available;
- request initiation and receipt times;
- known-not-sent, sent, known-success, known-failure, or ambiguous state;
- bounded status/usage/error metadata;
- reconciliation status/time; and
- no credentials, full prompt/response, manuscript, private artifact, or raw headers.

Before calling a provider, the worker writes durable effect intent in a short transaction when ambiguous repetition matters. It then releases the transaction, makes the call, and records outcome in another short transaction.

Provider idempotency keys are used when supported and scoped correctly. They supplement local records; they do not prove exactly-once processing, current authorization, or provider retention.

On timeout/network loss after a possible send, the worker does not assume failure and automatically retry a billable, publishing, notification, destructive, or otherwise non-idempotent effect. It queries provider status/receipts where possible, waits for reconciliation, or requires deliberate owner/operator action.

Known provider success is still non-authoritative application data. Applying an AI result or other creative mutation revalidates current Workspace/Scene/lifecycle/concurrency and commits through ordinary services.

Compensating effects, when possible, are new explicit effects with their own authority/idempotency/provenance. They are not database rollback.

## Transaction Boundaries

### Domain commit and follow-up Job

Domain mutation, Mutation Operation, and Job dispatch row commit atomically where follow-up is required. The Job is not visible before commit.

### Enqueue-only request

Authorization, Idempotency Record, Operation, and Job creation occur in one short transaction. The response follows commit.

### External provider call

Claim/attempt/effect-intent transaction ends before network I/O. After the response, a short transaction records receipt/status. No database locks span the call.

### Authoritative domain commit from Job

The worker reloads Account/service grant, Workspace, target, lifecycle, current version/revision, source records, and cancellation/lease state. It then commits conditionally through ordinary mutation services. A stale result does not overwrite current data.

### Protected artifact production

The Job creates/transfers an artifact outside a long transaction, verifies integrity, then records protected artifact metadata/result in a short transaction. A partially created artifact is not published as complete and is later cleaned/reconciled.

### Failure after external effect before local commit

The effect remains ambiguous or known-success based on provider evidence. Redelivery first reconciles; it does not blindly repeat.

### Worker crash/redelivery

Lease expires, a later worker claims, reads prior Attempts/effect records/idempotency, revalidates state, and resumes only from a safe checkpoint or reconciliation path.

Transaction syntax, isolation, claim query, and lock statements remain implementation details. Short explicit boundaries are mandatory.

## Authorization Revalidation

Enqueue authorization proves the initiator was permitted to request the operation at that time. It does not authorize execution indefinitely.

Before meaningful effects, workers revalidate:

- Account/service identity and current credentials;
- active Workspace Grant or narrowly approved service authority;
- direct Workspace scope of Job and every target/source;
- record existence without leaking inaccessible records;
- lifecycle state and allowed operation;
- current version/revision/preconditions;
- cancellation/quarantine/lease ownership;
- size/rate/cost/provider limits;
- source-content/context manifest validity; and
- current external integration grant where applicable.

Revoked grants, disabled Accounts, moved/mismatched records, trashed/archived prohibited targets, expired operations, superseded sources, or stale versions fail closed. The worker does not widen scope, switch Workspace, or infer approval.

Jobs applying AI/import results cannot make content Canon or authoritative without the explicit owner action and ordinary mutation rules already represented.

Manual retry and recovery reclassification perform current authorization again. Staff/superuser/database-admin status alone is insufficient.

## Workspace Scoping

Every Job handling private data has direct Workspace scope. Attempts, Idempotency Records, effect evidence, artifact references, target/source references, and Mutation Operation relationships must match that Workspace where applicable.

Cross-Workspace keys, targets, sources, provider results, artifacts, or restored job references fail structurally where constraints can enforce them and through service validation otherwise.

Queue polling may scan eligible operational metadata across Workspaces using a least-privileged service, but the claimed handler receives only one Job's Workspace/reference scope and reauthorizes data access. It never loads an unrestricted Workspace set into payload or logs.

Global maintenance Jobs, if later needed, use explicit system scope and bounded child work; they do not fake a Workspace or bypass per-Workspace effects.

Job IDs, queue names, correlation IDs, object keys, provider IDs, URLs, leases, and worker names are locators/metadata, not authorization.

## Progress and Result References

Progress is advisory and privacy-safe. It may include a bounded phase, percentage where meaningful, processed/total counts, and updated time. It cannot imply that an external or authoritative effect committed.

Progress updates are rate-limited/coalesced to avoid database/telemetry load. Exact cadence and frontend transport are later decisions. Browser polling, server-sent events, or another progressive mechanism may display status after ordinary authorization.

Status categories distinguish queued, running, waiting, cancellation-requested, succeeded, failed, cancelled, and quarantined without exposing private input or inaccessible target existence.

Successful Jobs reference:

- authoritative domain records created through ordinary transactions;
- AI Suggestion or staged import records;
- protected export/archive/backup artifact metadata;
- restoration verification report;
- derived projection generation/version; or
- bounded external-effect receipt.

Large results, manuscripts, prompts, provider responses, archives, and files are never embedded in Job rows. Protected artifacts use authorization, integrity, retention, and short-lived download access.

## Failure, Quarantine, and Manual Retry

Failed-terminal means the Job completed with a non-retryable outcome. Quarantined means execution is prohibited pending reconciliation, restore review, ambiguity resolution, unsupported version handling, or security/operator decision.

A dead-letter view may list failed-terminal/quarantined Jobs. It is not a generic broker feature requirement or creative history.

Poison Jobs are bounded by attempt budget and state transition; they cannot loop indefinitely. Queue-flood/rate controls prevent one job type or Workspace from starving others.

Manual retry requires:

- authenticated current actor/operator;
- Workspace and operation authorization;
- recent authentication for high-impact work;
- review of prior attempts/effect ambiguity;
- current target/lifecycle/version checks;
- an explicit retry/reconciliation choice;
- new attributable Attempt or Job identity as policy requires; and
- preservation of prior failure history.

No operator silently edits state to queued, resets attempt count, deletes evidence, or fabricates provider failure. Exceptional repair uses documented bounded procedure/security evidence.

User-facing errors provide safe categories and next steps, not stack traces, private titles/content, provider payloads, secrets, SQL, internal paths, or inaccessible-record confirmation.

## Restore and Recovery Reconciliation

After database backup or same-archive restoration, unfinished Job state is untrusted operational state even when structurally valid.

Before workers resume:

1. disable polling/execution in the isolated restored environment;
2. invalidate all prior leases, worker ownership, and heartbeats;
3. preserve succeeded, failed-terminal, and cancelled history;
4. transition queued, available, running, retry-wait, cancellation-requested, and ambiguous work to quarantined or a recovery-review state;
5. reconcile external-effect receipts/provider status before any retry;
6. verify Idempotency/Mutation Operation/result references and artifact existence/integrity;
7. classify each unfinished Job as safe to regenerate, safe to retry, requires reconciliation, terminal, or cancelled;
8. require owner/operator review for destructive, billed, publishing, notification, backup deletion, restore, or ambiguous provider work;
9. regenerate rebuildable search/projection Jobs instead of trusting old progress when safer;
10. reconcile unfinished exports/backups/restores and never expose partial artifacts;
11. rotate/revalidate worker/provider credentials separately from restored data; and
12. record bounded recovery decisions without manuscript content.

No restored Job resumes blindly. A Job safe before the backup may be unauthorized/stale now, and an external provider effect may have occurred after the recovery point.

Point-in-time recovery creates special ambiguity: local records can predate provider effects that occurred later. Provider reconciliation and deliberate owner decisions are required.

Job cleanup does not run until recovery verification preserves necessary evidence.

## Retention and Cleanup

Retention balances debugging/reconciliation/recovery/security evidence against privacy and database growth.

- Successful Jobs retain bounded summary/result references for a policy period.
- Failed-terminal and quarantined Jobs retain attempts/effect evidence longer where reconciliation or incident review requires it.
- Attempt history is bounded but not replaced solely by logs.
- Idempotency Records remain at least through the retry/ambiguity window; expiry semantics are explicit.
- External-effect evidence remains while provider ambiguity, billing, publication, notification, or compensation may need reconciliation.
- Security events follow their separate retention policy.
- Manuscript/prompts/responses are not retained in these operational records.
- Large/transient artifacts have separate retention and cleanup.
- Cleanup is a scheduled bounded Job/operation with least privilege and idempotency.
- Referential protection prevents cleanup of records still referenced by Mutation Operations, authoritative results, active Jobs, recovery reports, exports, or backups.
- Deleting Job/Attempt/Idempotency records never cascades to Scene, Revision, Mutation Operation, AI Suggestion, import records, exports, archives, or backups.

Exact durations, batch sizes, archival/offloading, purge strategy, and whether operational records enter structured archives remain later policy. Database backups may contain them; restore reconciliation still applies.

Retention is not proof of effect success. Cleanup is not domain purge and cannot erase creative history or security evidence required by policy.

## Background Worker and Operator Authority

Workers use separate least-privileged database/provider/storage credentials from browser/application, migration, backup, and restore roles where practical.

Worker authority is bounded by Job type, Workspace, targets, operation, provider, size/rate/cost, artifact destination, and time/preconditions. A service identity is not an Account and cannot create authorial approval.

Operators may inspect bounded Job metadata and retry/quarantine controls according to current authorization. They do not routinely view manuscripts, prompts, provider responses, archives, or credentials. Emergency access is attributable and minimized.

Staff/superuser or database-admin status does not automatically authorize job execution, retry, cancellation, artifact download, restore activation, or creative mutation.

Credential rotation invalidates affected leases/access. Compromised workers are isolated, credentials revoked, Jobs quarantined/reconciled, and external effects assessed before resumption.

Scheduled job creation uses a bounded scheduler identity. Scheduler decides when to create/enable Job intent; worker performs execution. Schedule configuration is not domain authorization and is revalidated.

## Django Application Boundary

Django services define Job types, payload/reference schemas, state transitions, authorization/revalidation, idempotency fingerprints, retry classification, cancellation checkpoints, external-effect handling, result commits, and privacy-safe errors.

Workers call the same application/query/domain services as interactive requests with an explicit service execution context. They do not write Scene pointers, revisions, lifecycle, grants, exports, or restoration state directly around domain services.

Transaction callbacks may notify/poke workers after commit but never provide sole durability. The committed Job row is authoritative.

Django model validation alone does not protect concurrent claims/transitions; PostgreSQL conditions/constraints and short transactions reinforce state. Exact ORM APIs, management commands, worker entrypoint, scheduler, and package are undecided.

No application code, models, migrations, commands, tasks, or tests are created by this ADR.

## PostgreSQL Boundary

PostgreSQL stores durable Job, Attempt, Idempotency, and bounded effect/dispatch state. It provides UUID identity, foreign keys, uniqueness, checks, atomic conditional updates, transactions, row locking, timestamps, and later selected indexes.

Database constraints should reinforce:

- valid Job/Attempt/Idempotency states;
- unique scoped idempotency keys;
- one Attempt number per Job;
- Workspace-consistent references;
- non-negative attempts/progress bounds where applicable;
- terminal/result consistency where row-local;
- lease-field consistency where row-local; and
- protective references to domain/operation/artifact records.

PostgreSQL `SKIP LOCKED` or equivalent patterns may support multi-worker claiming, but exact SQL/lock/fairness design is deferred. Advisory locks may assist specialized global work but do not replace durable leases/state and require connection-lifecycle caution.

Database time may anchor lease/availability comparisons. Constraints cannot enforce authorization, provider outcome, idempotent semantics, or cross-row workflow meaning alone.

PostgreSQL is the Version 1 queue durability mechanism, not a claim that it scales indefinitely. A future broker may deliver Job IDs while PostgreSQL remains authoritative for state/semantics.

## Rationale

A PostgreSQL-backed queue matches the modular monolith, requires no new broker failure domain, and can atomically couple Job creation to authoritative commits. This removes the most dangerous dispatch gap while keeping future broker migration possible.

At-least-once semantics reflect real crash/network behavior. Idempotent handlers, durable request fingerprints, leases, attempts, and reconciliation provide practical correctness without an impossible cross-system exactly-once claim.

Separate Job, Attempt, Idempotency, Mutation Operation, Security Event, and provider-effect meanings keep execution state from contaminating creative history/provenance or becoming authorization.

Short transactions around state/effect intent and post-provider revalidation protect database concurrency and prevent slow external systems from holding locks. Restore-time quarantine protects against repeating effects that occurred outside the restored recovery point.

Reference-minimized payloads and bounded evidence reduce privacy exposure and make authorization/current-state revalidation explicit.

## Decision Criteria

Options are evaluated against:

1. atomic dispatch durability after authoritative commits;
2. correctness under crashes, redelivery, retries, and ambiguous outcomes;
3. Workspace isolation and current authorization;
4. compatibility with Scene concurrency/immutable history;
5. bounded external/provider effects and costs;
6. privacy-safe payloads, logs, errors, and retention;
7. cancellation/status honesty;
8. restore and disaster-recovery reconciliation;
9. maintainability for one owner and modular monolith;
10. replaceable queue mechanism without semantic migration;
11. operational observability without manuscript leakage;
12. least privilege and operator/creative-authority separation; and
13. bounded implementation/operational complexity.

## Alternatives Considered

### Synchronous-only execution

Rejected as the complete model. It simplifies consistency but blocks requests during provider/export/backup/restore/search work and handles retries/status poorly. Small bounded work remains synchronous.

### Database-backed polling queue

Selected for Version 1. It atomically couples dispatch and state in PostgreSQL with low infrastructure overhead. Polling/load/fairness must be tested.

### Direct external broker publishing

Rejected initially. Publish-before-commit can execute rolled-back work; publish-after-commit can lose work. A broker adds another operational system.

### Transactional outbox feeding a broker

Strong future option. It preserves commit coupling and scalable delivery, but needs relay/broker/reconciliation infrastructure not justified initially.

### Job row as the outbox

Selected. The committed Job is both durable intent and executable state, avoiding duplicate tables/materialization gaps.

### Separate Dispatch/Outbox row

Deferred until an external broker or multi-destination dispatch requires separate delivery state.

### Post-commit callback without durable record

Rejected as sole dispatch because the process can fail after commit before callback/publish. Allowed only as wake-up optimization.

### At-most-once delivery

Rejected because crash/lost acknowledgement can lose required work. It does not guarantee effect uniqueness either.

### At-least-once with idempotent handlers

Selected. Duplicates are expected and controlled.

### Exactly-once claims

Rejected across PostgreSQL/providers because independent systems and ambiguous network outcomes prevent a universal atomic guarantee.

### One Job table only

Insufficient for bounded attempt/worker/effect/recovery evidence unless it becomes an overwritten history blob.

### Job plus append-oriented attempts

Selected. Job provides current summary; Attempts preserve execution evidence.

### Attempt details in logs only

Rejected because logs are ephemeral, privacy-risky, and not durable reconciliation state.

### Idempotency key only

Rejected because the same key could be reused with materially different input without detection.

### Key plus request fingerprint

Selected with caller/Workspace/operation scope.

### Idempotency in cache only

Rejected because eviction/outage permits unsafe replay.

### Durable PostgreSQL idempotency

Selected.

### Fixed retry delay

Simple but causes synchronized repeated load and adapts poorly. Not selected.

### Exponential backoff with jitter

Selected with bounded budgets and failure classification.

### Unlimited retries

Rejected due to poison loops, costs, queue starvation, and provider abuse.

### Bounded retry budgets

Selected; exact values deferred.

### Hard process termination for cancellation

Rejected as ordinary cancellation because it creates lease/effect ambiguity and cannot undo commits.

### Cooperative cancellation

Selected with safe checkpoints.

### Application-only worker claim

Rejected without database atomicity because multiple workers can claim concurrently.

### Database lease

Selected. It supports crash recovery while acknowledging duplicates remain possible.

### Long transaction across provider call

Rejected due to locks, pool exhaustion, timeouts, rollback ambiguity, and inability to atomically include provider state.

### Provider call outside transaction with revalidation

Selected with durable intent/effect evidence.

### Automatic retry after ambiguous outcome

Rejected for non-idempotent/billed/destructive effects.

### Reconciliation before retry

Selected.

### Resume all restored jobs

Rejected because authority/state/external effects may differ from the recovery point.

### Quarantine restored unfinished jobs

Selected.

### Keep full payloads

Rejected due to privacy, staleness, retention, and duplication.

### Reference authoritative/staged records

Selected with execution-time revalidation.

### Delete jobs immediately

Rejected because idempotency, reconciliation, recovery, and debugging evidence disappears.

### Bounded operational retention

Selected; durations deferred.

### One generic event table

Rejected. It would blur job state, provenance, idempotency, security evidence, and domain history into one weak schema.

### Separate Job, Mutation Operation, Idempotency, and Security Event records

Selected with explicit references where useful.

## Comparative Assessment

### Queue and dispatch strategy

| Strategy | Commit coupling | Operations | Future scale | Decision |
| --- | --- | --- | --- | --- |
| Synchronous only | Direct | Lowest | Poor for long work | Insufficient |
| DB Job polling | Atomic | Low/moderate | Moderate | Selected V1 |
| Direct broker publish | Gap risk | Higher | Strong | Rejected |
| Outbox + broker | Atomic via relay | High | Strong | Future option |
| Callback only | Non-durable gap | Low | Weak | Rejected sole path |

### Delivery guarantee

| Model | Lost work risk | Duplicate risk | External truth | Decision |
| --- | --- | --- | --- | --- |
| At-most-once | High | Lower | Still ambiguous | Rejected |
| At-least-once | Low | Expected | Reconcile/idempotent | Selected |
| Exactly-once claim | Misleading | Hidden | Impossible generally | Rejected |

### Job-attempt representation

| Model | Current query | History | Privacy/control | Decision |
| --- | --- | --- | --- | --- |
| Job only | Strong | Weak/overwritten | Moderate | Insufficient |
| Job + Attempts | Strong | Bounded durable | Strong | Selected |
| Logs only | Weak | Ephemeral | Leakage risk | Rejected |

### Idempotency strategy

| Strategy | Restart-safe | Input mismatch | Scope | Decision |
| --- | --- | --- | --- | --- |
| Key only | If durable | Undetected | Ambiguous | Rejected |
| Cache key/fingerprint | No | Detectable until eviction | Scoped | Rejected core |
| PostgreSQL key + fingerprint | Yes | Rejected | Workspace/caller/op | Selected |

### Cancellation strategy

| Strategy | Effect safety | Responsiveness | Decision |
| --- | --- | --- | --- |
| Delete Job row | Unsafe/evidence loss | Fast appearance | Rejected |
| Kill process | Ambiguous | Immediate process stop | Emergency only |
| Cooperative checkpoints | Explicit | Bounded delay | Selected |
| Compensating action | New effect | Varies | Separate when supported |

### External-effect handling

| Strategy | Duplicate risk | Ambiguous timeout | Decision |
| --- | --- | --- | --- |
| Call inside DB transaction | Still present | Unresolved | Rejected |
| Blind retry | High | Repeats effect | Rejected |
| Provider key only | Reduced | Provider-dependent | Supporting only |
| Durable intent + receipt + reconciliation | Lowest practical | Explicit | Selected |

### Restore-time behavior

| Strategy | Duplicate external effects | Recovery effort | Decision |
| --- | --- | --- | --- |
| Resume all | High | Low initially | Rejected |
| Cancel all | May lose safe work | Moderate | Too blunt |
| Quarantine/classify/reconcile | Controlled | Highest | Selected |
| Regenerate derived only | Safe for subset | Moderate | Selected where applicable |

### Retention strategy

| Strategy | Reconciliation evidence | Privacy/storage | Decision |
| --- | --- | --- | --- |
| Immediate deletion | Weak | Lowest | Rejected |
| Indefinite full payload | Strong but excessive | Worst | Rejected |
| Bounded metadata/attempt retention | Strong enough | Controlled | Selected |
| Logs only | Weak | Uncontrolled | Rejected |

## Evidence

### Repository evidence

- Product principles require privacy, authorial control, bounded AI, provenance, reversibility, backup, and recovery.
- Version 1 needs background execution for reliable AI/export/backup/restore/search work without weakening the private writing workflow.
- Architecture overview defines bounded Jobs, meaningful status, safe retries, and server authority while leaving the queue product open.
- Security architecture requires least privilege, Workspace authorization, secret isolation, safe logs, bounded jobs, and recovery reconciliation.
- AI context requires unknown provider outcomes not be blindly resubmitted.
- ADR-0001 through ADR-0009 establish trust, transactions, idempotency, operations, schema, authentication, exports/backups/restoration, and quarantine requirements.
- The architecture handoff recommends jobs/idempotency/transactional dispatch after recovery boundaries.
- The Story Engine audit rejects browser-side broad authority and unverified operations and supports rebuilding around bounded server-side services.

### Official and conceptual guidance reviewed

- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [Django database queries](https://docs.djangoproject.com/en/stable/topics/db/queries/)
- [Django migrations](https://docs.djangoproject.com/en/stable/topics/migrations/)
- [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL SELECT locking and SKIP LOCKED](https://www.postgresql.org/docs/current/sql-select.html)
- [PostgreSQL advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)

Provider-neutral distributed-systems reasoning supports at-least-once delivery, durable intent, idempotent handlers, bounded leases, and reconciliation because independent systems cannot participate in one atomic exactly-once transaction.

### Evidence still required

Before acceptance or implementation:

- select supported Django/PostgreSQL versions and prototype atomic claim patterns;
- measure polling load/fairness with synthetic queues;
- define exact Job/Attempt/Idempotency/effect fields and state transitions;
- define stable payload schemas and privacy-safe canonical fingerprints;
- prototype commit-coupled Job creation and rollback;
- test duplicate claims, lease expiry, late heartbeat, shutdown, and redelivery;
- classify every planned Job type's retry/cancellation/reconciliation behavior;
- test provider timeout before/during/after send with synthetic adapters;
- define worker/service/database/storage/provider least-privilege roles;
- define queue/rate/cost/concurrency controls and starvation policy;
- define artifact partial-state cleanup and protected access;
- define restore-time quarantine/classification procedures;
- define bounded retention and cleanup constraints;
- test logs/metrics/errors for content/title/prompt/secret absence;
- verify backup/archive treatment of operational records; and
- conduct synthetic deployment/restart/database-restore reconciliation exercises.

## Consequences

### Positive

- Domain commit and dispatch cannot separate through a publish gap.
- Version 1 adds no external broker failure domain.
- At-least-once/idempotent semantics match real failure behavior.
- Attempts preserve bounded reconciliation evidence.
- Durable fingerprints prevent conflicting key reuse after restart.
- Leases recover work after worker crashes.
- Short transactions avoid holding locks during providers/artifacts.
- Revalidation prevents stale/revoked Jobs from acting.
- Restore quarantine prevents duplicate external effects.
- Queue mechanism can evolve without changing Job identity/authority semantics.

### Negative

- PostgreSQL polling adds database load and queue-specific indexes/cleanup needs.
- At-least-once handlers and reconciliation are more complex than happy-path tasks.
- Job/Attempt/Idempotency/effect records increase schema/operational state.
- Lease expiry can create concurrent late workers and duplicates.
- Cooperative cancellation cannot stop every provider call immediately.
- Conservative ambiguous-outcome handling can delay results.
- Execution-time authorization may make previously accepted Jobs fail later.
- Retention/cleanup must balance evidence and privacy.
- Restore reconciliation is operationally demanding.
- A future external broker requires relay/delivery migration.

### Neutral or Operational

- Exact labels, timings, limits, priorities, and indexes remain later work.
- Scheduler remains separate from worker semantics.
- Some bounded work stays synchronous.
- Job progress may be approximate.
- Provider-specific operation tables may be added later.
- Terminal/quarantined records are operational, not creative history.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Job committed but never noticed | Lost follow-up | Durable polling of committed rows; callbacks only optimization | Poller outage delays work |
| Worker claims same Job twice | Duplicate effects | Atomic claim/lease, idempotent handler, effect reconciliation | Expiry/partition permits overlap |
| Lease expires during long call | Concurrent attempts | Heartbeats, checkpoints, effect intent/idempotency, reconciliation | Paused/partitioned worker can continue |
| Blind retry duplicates provider effect | Cost/publication/destruction | Ambiguous state and reconciliation before retry | Provider may lack status API |
| Idempotency key reused with new input | Wrong result | Scoped canonical fingerprint mismatch rejection | Canonicalization bugs remain |
| Idempotency expires too soon | Unsafe replay | Retention covers risk/ambiguity window; high-risk effect evidence longer | Exact window is hard to know |
| Job payload leaks manuscript | Privacy breach | Stable references, allowlisted schemas, no content/logging tests | References/metadata remain sensitive |
| Worker grant revoked after enqueue | Unauthorized access | Execution-time revalidation | Race before an external call remains possible |
| Stale Job overwrites Scene | Lost work | Recheck version/current revision and ordinary save transaction | Job becomes terminal conflict |
| Cancellation presented as rollback | False expectation | Separate requested/acknowledged/effect states and clear UX | External effect may remain |
| Retry storm overloads DB/provider | Availability/cost | Exponential jitter, budgets, rate/concurrency limits, poison quarantine | Broad outage still creates backlog |
| Polling starves low priority Jobs | Delayed work | Fair claim policy, aging/limits, metrics | Exact fairness needs evidence |
| Attempts retained forever | Privacy/storage growth | Bounded retention and cleanup | Reconciliation requirements vary |
| Cleanup deletes evidence | Unsafe replay/investigation loss | Referential protection and policy classification | Operator mistakes remain |
| Restored jobs resume blindly | Duplicate external effects | Quarantine all unfinished, invalidate leases, reconcile | Manual recovery cost |
| PITR forgets later provider effect | Duplicate effect | Provider receipt reconciliation and deliberate review | External evidence may be unavailable |
| Worker credential compromised | Workspace/provider exposure | Least privilege, rotation, quarantine, access events | Worker necessarily handles some plaintext |
| Operator retry bypasses authority | Unauthorized effect | Current auth/recent auth and attributable services | DB admins retain technical capability |
| Job state diverges from Attempts | Wrong status | Transactional transitions and integrity reconciliation | Repair may be needed after corruption |
| Database queue scales poorly | Latency/load | Measure/index/batch; later outbox+broker migration | Migration adds operational complexity |

## Security and Privacy Review

- Security-sensitive: Yes; Jobs may access private manuscripts, providers, archives, backups, and restoration controls.
- Primary references: `docs/architecture/security.md`, `docs/architecture/overview.md`, ADR-0001 through ADR-0009.
- Additional references: data model, AI context, integrations, product docs, architecture handoff, and Story Engine audit.

### Assets and threats

Assets include Job/Attempt/Idempotency/effect records, worker/provider/storage credentials, private targets, artifacts, AI contexts/results, exports, backups, restoration state, and operator controls. Threats include cross-Workspace access, queue flooding, poison jobs, retry storms, duplicate provider effects, SSRF/path/object-key injection, payload/log leakage, compromised workers, stale restored credentials, and unauthorized manual retry.

### Least privilege and isolation

Workers receive only required database/provider/storage permissions. Job type and Workspace constrain every operation. Provider credentials are isolated per capability where practical and never placed in payloads/browser/logs.

Future URL fetching, object access, paths, and artifact destinations use allowlisted purpose, safe typed references, SSRF controls, traversal protection, size limits, integrity checks, and private access. Jobs cannot interpolate untrusted data into shell commands or SQL.

### Logging and errors

Logs/metrics use job type, state, duration, bounded attempt/error classes, counts, and non-secret correlation IDs. They exclude titles, manuscripts, prompts, responses, import bodies, archive contents, credentials, tokens, full URLs/query strings, headers, object paths, and stack locals.

Security events record high-impact enqueue/cancel/manual retry/quarantine/restore decisions without duplicating Job payload or creative content.

### Availability and abuse

Rate, concurrency, queue-depth, payload-size, cost, Workspace, provider, and retry limits prevent abuse. Poison Jobs terminate/quarantine. Owner-visible status distinguishes backlog/provider outage from completed effects.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- enqueue authorization, Workspace scope, CSRF/recent-auth where applicable;
- atomic domain commit+Job and full rollback;
- duplicate delivery/claim, lease expiry, heartbeat delay, worker crash, shutdown, and late worker;
- scoped idempotency key/fingerprint same/different input;
- every failure-class retry/terminal/reconciliation decision;
- cancellation before claim, during work, after send, and after commit;
- provider success/failure/timeout/ambiguous receipt and no blind retry;
- stale Scene/lifecycle/grant/current-version revalidation;
- attempt evidence and Job-summary integrity;
- progress/result authorization and no content leakage;
- artifact partial/final integrity/access/cleanup;
- queue flooding, retry storms, poison work, starvation, and limits;
- restored-job quarantine, lease invalidation, external reconciliation, and safe derived regeneration;
- cleanup referential protection and no domain cascade;
- credential rotation/compromised-worker containment; and
- absence of manuscripts/prompts/responses/secrets/titles from payloads, logs, metrics, URLs, errors, and security events.

### Residual risk

Workers necessarily access some plaintext/private data and provider credentials. PostgreSQL queue load can affect interactive traffic. Leases cannot prevent a partitioned worker from continuing. Providers may offer no reliable receipt/reconciliation API. Operator/database compromise can alter operational state. Conservative quarantine/revalidation can delay work and require manual resolution.

## Product and Architecture Alignment

### Product alignment

The architecture keeps long-running work reviewable, private, recoverable, and subordinate to authorial control while avoiding silent duplicates or provider authority.

### Scope alignment

It supports the one narrow AI capability, search/projection rebuild, export, backup, restoration, and future import without selecting or implementing those subsystems or expanding collaboration.

### ADR alignment

- ADR-0001: workers are bounded server-side principals.
- ADR-0002: workers share the modular-monolith Django codebase.
- ADR-0003: PostgreSQL provides durable state/transactions.
- ADR-0004: Job effects obey concurrency/idempotency and no blind provider retry.
- ADR-0005: service identity, Account, recent authentication, and administrative authority remain distinct.
- ADR-0006: Jobs reference content; payloads do not become authoritative or leak manuscripts.
- ADR-0007: supporting records remain separate from creative domain/provenance/security.
- ADR-0008: UUID/Workspace/Mutation Operation/constraint/migration boundaries guide future records.
- ADR-0009: backup/export/restore Jobs use bounded authority and restored work is quarantined/reconciled.

### Architecture alignment

The selected model preserves Django policy, PostgreSQL authority, provider isolation, rebuildable derived data, safe recovery, secret/log boundaries, and replaceable integrations.

### Normative-document impact

If accepted, architecture overview, security, AI-context, integration, backup/restoration, and data-model documents should be reconciled with PostgreSQL-backed Job/Attempt/Idempotency semantics, commit coupling, leases, retry classification, external-effect reconciliation, and restore quarantine. The ADR index should then be updated. No other file is changed by this Proposed ADR.

## Migration and Portability

Stable UUID Job/Attempt/Idempotency/Operation identity and constrained semantics are independent of a specific queue library. A future broker carries Job identity/delivery hints while PostgreSQL remains authoritative or migrates through an explicit ADR.

Schema migration preserves Job states, attempts, idempotency scopes/fingerprints, effect evidence, Workspace references, results, cancellation, and quarantine. Migration does not resume work automatically.

Database backup may include operational records. Structured archive includes only operation/idempotency/job evidence required for authoritative semantics/recovery under ADR-0009; portable archives must not reactivate Jobs.

Restoration invalidates leases and quarantines unfinished work regardless of queue mechanism. Provider changes retain local effect/operation IDs and map provider receipts as external references.

A broker migration must preserve commit-coupled durability, at-least-once expectations, idempotency, authority, cancellation, attempt evidence, and reconciliation. It cannot redefine delivery acknowledgement as effect success.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Define exact Job, Attempt, Idempotency, and bounded effect fields/state transitions in a later physical-schema decision.
- [ ] Select supported Django/PostgreSQL versions and prototype atomic claim patterns after implementation authorization.
- [ ] Define Job-type registry and versioned payload/reference schemas.
- [ ] Define privacy-safe request fingerprint canonicalization.
- [ ] Define Workspace composite constraints and protective deletion.
- [ ] Define claim fairness, priority, lease/heartbeat, polling, batch, and concurrency policies.
- [ ] Classify retry/cancellation/reconciliation for AI, export, backup, restore, import, search, cleanup, and artifact Jobs.
- [ ] Define provider effect receipt/reconciliation interface.
- [ ] Define worker/service/database/provider/storage least-privilege roles.
- [ ] Define rate, queue-depth, payload, size, cost, and retry-storm limits.
- [ ] Define progress/status/result API boundary without choosing frontend transport prematurely.
- [ ] Define artifact partial/final states, integrity, authorization, and cleanup.
- [ ] Define restore-time Job quarantine and recovery-review procedure.
- [ ] Define bounded retention/cleanup and backup/archive inclusion.
- [ ] Define deployment shutdown/drain and worker credential rotation.
- [ ] Add later unit, integration, concurrency, adversarial, provider-failure, deployment, backup, and restoration tests using synthetic data.
- [ ] Evaluate external broker only after measured PostgreSQL queue limits or deployment needs justify it.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes Django initialization, code, models, migrations, database objects, SQL, shell scripts, workers, commands, tasks, queues, schedulers, brokers, providers, Redis, RabbitMQ, cloud services, systemd, containers, packages, tests, production data, deployment, modification of the old Story Engine, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No queue, worker, scheduler, broker, task library, database table, Django model/migration/command, job, script, provider integration, test, package, Redis/RabbitMQ/PostgreSQL worker configuration, system service, container, cloud service, timing value, retry count, lease, retention, or concurrency limit is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
