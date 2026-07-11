# ADR-0011: AI Provider Boundary, Suggestion Records, and Human Approval

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 boundaries for AI provider access, request and response records, prompt and context construction, private manuscript handling, staged AI Suggestions, human review and application, provenance, background execution, idempotency, ambiguous outcomes, provider retries, cost and rate controls, portability, retention and deletion, secrets, logging, Workspace authorization, stale sources, recovery, and failure isolation, while the exact provider, model, SDK, endpoint, prompt wording and templates, context-manifest and output schemas, source-hash canonicalization, raw-response retention and encryption, suggestion-retention periods, limits and budgets, usage normalization, provider idempotency and reconciliation APIs, secret manager, database fields and indexes, rendering and review interface, job configuration, archive inclusion, and deployment details remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; AI architecture, Django, PostgreSQL, security, privacy, authorization, provenance, content/revision, jobs, recovery, and provider-portability perspectives

## Context

Strange Novelty includes one narrow, explicitly invoked Version 1 AI capability: scene-focused review. The provider receives private manuscript content across an external trust boundary, returns untrusted output, may retain/process data under provider terms, may charge per request, and may produce delayed, malformed, duplicated, or outcome-unknown responses.

The old Story Engine called providers from browser/webview code, stored credentials alongside general settings, assembled context through ad hoc and sometimes broad fallbacks, and allowed some generated text to move directly into authoritative fields. Strange Novelty must not copy that trust model, provider coupling, or authority path.

ADR-0001 through ADR-0010 establish controlling boundaries. The browser is untrusted. Django is the policy boundary. PostgreSQL is authoritative. Every private operation is authenticated, authorized, Workspace-scoped, and revalidated. Scene Revision contains immutable authoritative text. AI output is non-authoritative. Applying content uses the ordinary Scene version/current-revision token and creates a new revision atomically. Mutation Operation, Job, Job Attempt, Idempotency Record, Security Event, and provider-effect evidence have distinct meanings. Provider calls occur outside long database transactions. Delivery is at-least-once, external outcomes may be ambiguous, and restored unfinished Jobs are quarantined.

The AI-context architecture additionally requires explicit invocation, narrow context, a context manifest, source-aware selection, exclusion of unrelated/imported/future-reveal material by default, prompt-injection resistance, provider-neutral request construction, visible usage, failure isolation, and no autonomous rewriting.

The decision must distinguish:

- provider request from Job;
- provider response from AI Suggestion;
- AI Suggestion from Scene Revision;
- AI Suggestion from Mutation Operation;
- suggestion generation from suggestion application;
- approval from execution;
- acceptance from Canon;
- provider metadata from authorization;
- prompt template from full prompt;
- source revision from current revision;
- stale source from provider failure;
- regeneration from retry;
- retry from duplicate delivery;
- cancellation from rollback;
- raw response from normalized suggestion;
- model portability from output equivalence;
- provider receipt from known success;
- known provider success from authoritative mutation;
- human-edited suggestion from original model output;
- partial acceptance from automatic merge;
- retention from domain history;
- suggestion deletion from applied-revision deletion;
- service identity from Account identity; and
- AI assistance from autonomous agency.

This ADR selects no vendor, model, SDK, embedding provider, vector database, retrieval framework, agent framework, tool-use protocol, web-browsing capability, file access, or provider-side retrieval.

## Decision

If accepted, Version 1 will use the following architecture.

1. All AI provider access occurs server-side through a provider-neutral AI adapter/gateway behind Django. The browser never holds provider credentials or calls a provider directly.
2. Version 1 supports one narrow scene-focused review capability. Tool use, agents, autonomous multi-step execution, web browsing, file access, code execution, provider-side retrieval, embeddings, and broad RAG are outside scope.
3. Every AI operation is explicitly invoked, authenticated, authorized, Workspace-scoped, rate/cost/size bounded, represented by an AI Request record, and executed using ADR-0010 Job/Attempt/Idempotency/lease/cancellation/reconciliation semantics.
4. Context is constructed server-side from an authorized manifest referencing exact source Scene Revision IDs, representation versions, and content hashes or equivalent integrity evidence. Unrelated Workspace content is excluded.
5. Operational records retain prompt-template/version IDs, source references/hashes, bounded configuration, provider/model metadata, request/receipt identifiers, usage/cost, and status—not manuscript bodies or full prompts by default.
6. Provider calls occur outside long database transactions. Before transmission, intent/context-manifest/effect evidence is committed; after response, a short transaction revalidates Job/Workspace/request state and persists a normalized AI Suggestion or bounded failure/outcome state.
7. Raw provider response is not the domain model. Valid provider output is parsed, size/schema validated, safely normalized, and stored as one or more distinct staged AI Suggestion records with bounded provenance.
8. AI Suggestion remains separate from Scene Revision, Mutation Operation, Job, Job Attempt, Idempotency Record, Security Event, provider-effect evidence, and raw response retention.
9. Provider output never automatically becomes authoritative, Canon, approved, or applied. Only an explicitly authorized human action may apply a suggestion.
10. Applying a suggestion reauthenticates/authorizes, checks current Workspace/Scene/lifecycle and source staleness, accepts explicit complete proposed content, and uses the ordinary Scene concurrency/idempotency transaction to create a new immutable Scene Revision and Mutation Operation.
11. Suggestion acceptance and Canon are distinct. Applying text does not automatically promote its state to Canon. Any Canon transition follows separate explicit authority rules.
12. Suggestions record source revision IDs/hashes, target Scene, provider/model/template/configuration metadata, AI Request/Job/operation references, creation time, normalized output, review state, and disposition/provenance sufficient for stale detection and portability.
13. Source revision mismatch makes a suggestion stale. Version 1 does not silently merge or force-apply stale output. The owner may compare/edit, refresh/regenerate, or deliberately create a new proposal against current state through ordinary conflict handling.
14. Partial acceptance and human editing produce explicit author-controlled proposed content. The original suggestion remains immutable evidence where retained; application records what was used and creates one ordinary new revision.
15. AI work uses durable local idempotency plus provider idempotency where supported. Provider support does not prove exactly-once behavior. Ambiguous outcomes are quarantined/reconciled before unsafe retry.
16. Cancellation is cooperative and cannot unsend a transmitted request. A response arriving after cancellation remains non-authoritative and is handled under explicit retention/disposition policy.
17. Cost, tokens, request/response size, concurrency, rate, retry, and Workspace/provider budgets are bounded. Exact values remain later operational decisions.
18. Provider credentials remain outside Git, browsers, Job payloads, logs, portable archives, prompts, context manifests, provenance, and suggestions. They use separate secret management and least privilege.
19. Full prompts and raw responses are not retained indefinitely by default. Prefer normalized suggestions and source/template hashes. Bounded encrypted raw-response retention may be enabled later for troubleshooting only under explicit access, duration, deletion, and backup rules.
20. AI output is untrusted text: escape/render safely and never execute it as code, SQL, shell commands, templates, URLs, paths, database instructions, tool calls, or policy.
21. Restored unfinished AI Jobs/effects are quarantined. Restored Suggestions remain non-authoritative and require current authorization/stale-source checks before application. Provider sessions/secrets are not restored from structured archives.
22. Deleting AI operational/request/suggestion records cannot delete authoritative Scene Revisions or Mutation Operations created through prior application.
23. Provider outage, rejection, malformed output, timeout, cancellation, cost/limit failure, or storage failure leaves authoritative content unchanged and ordinary workspace use available.

## Terminology and Boundaries

An **AI Request** is the local authorized description/status of one provider-facing task. A **Job** schedules/executes it. A **provider request** is the external transmission created by the adapter. These records may reference one another but are not interchangeable.

A **provider response** is untrusted external data. A **raw response** is its provider-specific representation. An **AI Suggestion** is a validated, normalized, staged local record derived from a response and explicitly marked non-authoritative.

**Generation** creates a Suggestion. **Review** presents it to the owner. **Approval/application** is a later explicit human action. Provider success does not imply approval, and application does not imply Canon.

A **source revision** is the exact immutable Scene Revision used as context. The **current revision** is the Scene's current pointer at review/application time. They may differ; that is staleness, not provider failure.

**Regeneration** is a new AI Request using newly authorized context. **Retry** is another attempt at the same material request after a safe retryable failure. **Redelivery** is duplicate execution of the same Job. Their identity/provenance must remain distinct.

**Partial acceptance** means the owner explicitly selects/edits a subset into new proposed authoritative content. It is not automatic merge. **Human-edited suggestion** is author input derived from model output, with derivation provenance preserved.

**Provider portability** means local records and workflows do not require one provider schema/ID to remain understandable. It does not promise different models will produce equivalent output.

## AI Architecture Principles

- AI assists; the author decides.
- Use one explicit narrow capability before expanding scope.
- Provider access is server-only and adapter-mediated.
- Providers receive one bounded request, not Workspace access.
- Context is exact-source, manifest-driven, minimized, and reviewable.
- Prompt content never grants policy or tool authority.
- Provider output is untrusted and staged.
- No automatic application, merge, Canon promotion, or source rewrite.
- Source revisions and hashes make staleness detectable.
- Application uses ordinary authorization, content normalization, concurrency, idempotency, revision, and provenance rules.
- External calls use ADR-0010 jobs and short transaction boundaries.
- Unknown outcomes are reconciled before unsafe retry.
- Records/logs prefer references, versions, hashes, and bounded metadata over private bodies.
- Failure cannot change authoritative content or block local authoring.
- Provider-specific concepts stay behind the adapter.
- Retention is explicit and privacy-minimized.

## Provider Adapter Boundary

The provider-neutral adapter is the sole outbound AI boundary. It:

- accepts an internal validated task package;
- maps provider-neutral task/configuration to one provider request;
- obtains server-side credentials through approved secret delivery;
- applies endpoint allowlists, authenticated transport, timeouts, request/response limits, and provider-specific idempotency where available;
- separates application instructions from quoted/untrusted creative context;
- sends no tools or provider-side retrieval capability in Version 1;
- records bounded provider request/response/receipt IDs and usage;
- validates/normalizes response status and structure;
- returns provider-neutral result/failure categories; and
- never writes domain content directly.

The adapter receives only the approved context manifest/material for one Request. It has no direct authority to browse the database, search broadly, access files/backups/exports, change Workspace records, apply Suggestions, or infer Canon.

Provider models/endpoints/options remain configuration behind the adapter. Provider names/model IDs may be recorded for provenance/cost/troubleshooting but are not stable application identity.

Provider callbacks, streaming, batch APIs, content moderation APIs, and model-specific features are deferred unless required by the selected narrow capability and separately reviewed.

## AI Request Record

An AI Request is a Workspace-scoped supporting record containing logically:

- stable UUID;
- direct Workspace;
- initiating Account and/or bounded service attribution;
- supported task type/version;
- target Scene and exact source Scene Revision references;
- source representation versions and content hashes;
- context manifest reference/hash/version;
- prompt-template ID/version;
- bounded provider-neutral configuration version/values;
- Job, Idempotency Record, Mutation Operation/operation intent references where applicable;
- constrained state;
- created/submitted/completed/cancelled timestamps;
- selected provider/model identifiers after dispatch;
- bounded request/response size, usage, cost, status, and error category;
- provider effect/request/receipt references; and
- result Suggestion references.

The record excludes full manuscript/context text, full prompt, raw response, credentials, tokens, request headers, secret configuration, private title, browser state, and unbounded provider errors.

The Request is not a Job: it describes AI task semantics and provenance, while Job describes execution. It is not an Idempotency Record, which deduplicates material invocation. It is not a Mutation Operation until/if an authoritative mutation occurs.

Request state may distinguish draft/previewed, queued, submitted, outcome-unknown, completed-with-suggestions, completed-no-suggestion, failed, cancelled, and quarantined concepts. Exact labels remain physical-schema work.

## Provider Effect and Response Boundary

Provider submission follows ADR-0010 external-effect handling. Before sending, the worker durably records effect intent, application idempotency identity, Request/Job/Attempt, provider/model/configuration, and context-manifest hash in a short transaction.

The provider call occurs outside that transaction. Afterwards the worker records known-not-sent, submitted, known-success, known-failure, or ambiguous outcome with bounded provider receipt IDs and usage metadata.

A provider receipt/request ID proves only that the provider recognized some request under its rules. It is not proof of semantic success, correct response, authorization, acceptance, or authoritative mutation.

The response pipeline:

1. enforces transport/size/time limits;
2. treats payload as untrusted data;
3. validates expected response type/schema/version;
4. rejects active content/instructions/tools/URLs as authority;
5. extracts only the bounded provider-neutral output required by the task;
6. safely normalizes a Suggestion representation without changing source content;
7. stores Suggestion(s) and Request outcome in a short transaction after revalidation; and
8. applies nothing to Scene.

Raw provider response is transient by default. If retained temporarily, it is encrypted/protected separately, linked to Request, access-restricted, excluded from routine logs and portable archives by default, and deleted under a short later policy.

## AI Suggestion Record

AI Suggestion is a distinct Workspace-scoped staged supporting record with:

- stable UUID;
- direct Workspace;
- AI Request reference;
- target Scene;
- exact source Revision IDs/hashes used;
- prompt-template/context-manifest versions/hashes;
- provider/model/configuration identifiers sufficient for provenance;
- normalized suggested text/structured output for the narrow capability;
- output schema/version;
- creation time;
- review state and timestamps;
- disposition: retained, rejected, expired, deleted, applied-whole, applied-part, superseded, or equivalent;
- optional human-edited derivative/application reference;
- applied Scene Revision and Mutation Operation references when applied;
- bounded usage/cost reference; and
- no live credentials or raw provider payload by default.

Suggestion text is private and untrusted. It follows Workspace authorization, output escaping, retention, export/archive, backup, deletion, and incident handling.

Suggestion is not Scene Revision: it does not become current content. It is not Mutation Operation: it explains proposed output, not a committed domain mutation. It is not Job or provider effect: it is the normalized staged result.

The original normalized Suggestion is immutable once review begins, except for bounded lifecycle/disposition fields. Human edits create a separate application draft/derivative relationship rather than overwriting model-origin evidence.

A Suggestion can be reviewed/rejected/deleted without affecting source Scene. Deleting an already applied Suggestion does not delete the applied Revision or Mutation Operation; provenance retains a bounded reference/tombstone under later policy.

## Source Revision and Staleness Model

Each Request/Suggestion records every authoritative source by stable record ID, exact revision ID, format/normalization version, and content hash/integrity evidence. Non-Scene sources later follow equivalent immutable-version references.

At review and application, Django compares:

- target Scene identity and Workspace;
- source Revision IDs/hashes from Request/Suggestion;
- target Scene current Revision and integer version;
- lifecycle/authorization/current source accessibility; and
- context-manifest constraints.

A Suggestion is stale when a source has changed, disappeared, moved outside authorization, changed lifecycle/state relevant to the task, or no longer matches its recorded hash/version. Stale does not mean malformed provider output; it means the evidence base differs.

Version 1 behavior:

- visibly warn and prevent direct one-click application to current content;
- permit comparison against source/current revisions;
- allow regeneration as a new Request using current authorized sources;
- allow the owner to copy/edit useful text into a new explicit proposal against current state; and
- rely on ordinary optimistic concurrency at final save.

The system does not automatically merge stale output, silently refresh its provenance, replace recorded source IDs, or force current content. “Apply despite stale” is rejected as a direct operation; deliberate owner editing produces new proposed content and records derivation.

Hash mismatch never broadens context or causes source content to be resent automatically.

## Human Review and Approval

Only the authenticated, currently authorized owner can review private Suggestions and decide their disposition. Review displays enough provenance to understand task, sources, source staleness, provider/model where useful, time, limitations, and AI-generated status.

Distinct actions include:

- retain as Suggestion;
- reject;
- expire or delete under policy;
- regenerate from current sources;
- apply whole after preview;
- select/apply part through explicit author editing;
- edit before application; and
- abandon due to staleness/conflict.

Approval means explicit intent to use proposed content in a specific domain mutation. It is not provider execution, Request completion, review acknowledgement, application success, or Canon promotion.

Applying may fail after approval because authorization changed, Scene became stale, lifecycle forbids editing, limits/normalization fail, CSRF/session expires, or transaction conflicts. Failure leaves Scene unchanged and Suggestion staged with clear status.

Staff/superuser, worker, provider, database administrator, or service identity cannot silently approve. Emergency repair cannot fabricate owner approval.

## Applying a Suggestion

Application is an ordinary domain mutation, not a privileged provider shortcut.

The flow:

1. owner opens an authorized Suggestion and current target Scene;
2. server revalidates Account, Grant, Workspace, Scene, Suggestion, sources, lifecycle, and staleness;
3. UI presents proposed complete content or explicit author-edited result and current concurrency token;
4. owner explicitly confirms application;
5. request uses current session, CSRF, authorization, normalization/limits, Scene version/current-Revision token, and Idempotency Record;
6. Django starts the ordinary short mutation transaction;
7. creates Mutation Operation with AI-assisted-apply source and Suggestion/Request provenance;
8. inserts a complete immutable Scene Revision;
9. advances Scene current pointer/version atomically if token still matches;
10. links Suggestion disposition to applied Revision/Operation; and
11. commits or rolls back all authoritative effects.

A stale/conflicting final token creates no Revision. Provider metadata and Suggestion ID grant no authority. The Job that generated the Suggestion never applies it automatically.

The new Revision contains exact authoritative normalized content, not a pointer to provider output. Deleting/provider outage later cannot remove the manuscript.

Application records AI derivation but does not mark content Canon. Content-state changes remain separate explicit operations.

## Partial Acceptance and Human Editing

Version 1 may allow the owner to select or copy part of a Suggestion and edit it before application. The result is explicit author-controlled proposed Scene content.

Partial acceptance:

- never runs automatic semantic/text merge;
- never mutates the prior/current Revision in place;
- preserves the original Suggestion where retained;
- records that the applied Revision was derived in part from Suggestion;
- distinguishes model output from subsequent author edits where practical without forensic keystroke tracking;
- submits complete final content through ordinary concurrency; and
- creates one new immutable Revision on success.

Human-edited Suggestion content should be represented as an application draft or explicit applied-content snapshot/reference, not by overwriting original normalized model output. Exact draft schema/UI is later work.

“Accept” does not mean every token came from the provider; “AI-assisted” provenance may remain appropriate after substantial author editing because origin is not erased. Exact thresholds/classification wording remain later product policy.

## Job, Idempotency, Retry, and Cancellation

AI generation uses ADR-0010 Job semantics:

- committed AI Request/Job dispatch before worker claim;
- PostgreSQL-backed durable Job/Attempt records;
- at-least-once delivery;
- leases and heartbeats;
- privacy-safe reference payloads;
- execution-time authorization/source revalidation;
- bounded retry classification/backoff/jitter;
- cooperative cancellation;
- provider effect intent/receipt evidence;
- quarantine and manual review; and
- restore-time reconciliation.

Local Idempotency Record is scoped to Workspace, caller, task, context-manifest/source hashes, template/configuration version, and key/fingerprint. Same key/different material request fails. Duplicate delivery returns/reconciles the existing Request/Suggestion rather than creating duplicate provider calls/results where possible.

Provider idempotency keys are used when available, derived/scoped without leaking secrets/content. They supplement local state and do not prove exactly-once.

Retryable failures include known-not-sent transient network failures, provider rate limits, and temporary provider/service failures within budget. Validation, authorization, unsupported schema, malformed output, safety rejection, stale source before submission, and permanent provider errors are terminal or require new owner action.

Timeout after possible transmission is ambiguous. Reconcile provider receipt/status before retry. If reconciliation is unavailable and duplicate billing/effects matter, quarantine and request deliberate owner action.

Cancellation before transmission prevents send. After transmission it cannot unsend; returned output may be discarded, retained briefly for reconciliation, or normalized only under explicit policy. Cancellation never rolls back a committed applied Revision.

Regeneration is a new authorized Request based on current context, not an automatic retry of stale output.

## Authorization and Workspace Scoping

Every Request, Job, Attempt, Suggestion, context manifest, source reference, effect, usage record, result, review, and application is Workspace-scoped.

Authorization is checked:

- when task/configuration/context preview is created;
- when Request/Job is committed;
- before worker retrieval of every source;
- immediately before provider transmission;
- before response/Suggestion persistence;
- whenever Suggestion/result is viewed;
- before retain/reject/delete/regenerate actions; and
- immediately before authoritative application.

The worker re-resolves current Account/service authority, Grant, source Workspace, target Scene, lifecycle, source Revision/hash, limits, and provider permission. Enqueue-time permission is insufficient.

Stable IDs, provider IDs, Request/Job/Suggestion IDs, context hashes, URLs, and possession of provider output do not grant access. Unauthorized failures avoid confirming private records.

Service identity may transmit an already authorized bounded Request but cannot approve/apply/Canonize it. Cross-Workspace context, Suggestions, application, or import fails closed.

## Prompt and Context Construction

Prompt/context construction is server-controlled and deterministic enough to explain what was sent without retaining full private bodies in operational records.

The internal task package contains:

- task type/version;
- prompt-template/instruction version;
- selected provider-neutral configuration;
- exact context manifest version/hash;
- stable source IDs and exact Revision IDs/hashes;
- bounded state/provenance/Creative Context/reveal metadata required for interpretation;
- explicit exclusions/one-operation overrides;
- source labels separating instructions from quoted content;
- output contract/version; and
- size/cost/response limits.

The provider request is rendered from that package and current verified source content. Records retain template/configuration/source references and hashes, not full assembled prompts by default.

Context is minimized to the purpose. No full Workspace, Book, database, directory, backup, export, unrelated drafts, rejected conflict content, browser state, clipboard, comments, hidden editor DOM, logs, credentials, or secret configuration is included.

Prompt injection inside story/import/AI text is untrusted content. It cannot expand context, request more retrieval, reveal hidden sources/secrets, invoke tools, browse, access files, change policy, apply content, or authorize follow-up work.

If source content changes between preview and submission, the Request fails/refreshes rather than silently sending a different context. Exact prompt wording/output schema remains later provider-neutral capability design.

## Privacy, Secrets, and Logging

Private manuscript content sent to a provider receives the same sensitivity as the archive. Provider selection later must review retention, training use, human review, subprocessors, region, deletion, incident, and contractual behavior.

Provider credentials:

- stay server-side in separately managed secrets;
- never enter Git, browser state, client bundles, Job payloads, Request/Suggestion/Operation records, manifests, prompts, logs, exports, structured archives, backups by default, or provider-visible request bodies;
- are scoped to the AI gateway/provider capability;
- support rotation/revocation and incident response; and
- are re-established/revalidated after restoration rather than activated from archives.

Routine logs/metrics/traces/errors contain only bounded Request/Job type, state, provider/model identifiers where safe, latency, token/usage/cost counts, response size, error category, rate-limit status, and non-secret correlation IDs.

They exclude manuscript/context text, full prompts/responses, Suggestions, titles, search terms, credentials, tokens, full provider URLs, headers, object paths, database queries, stack locals, and unauthorized identifiers.

AI output is escaped/safely rendered. No response-supplied HTML, Markdown, URL, code, tool call, path, SQL, template, or instruction executes. Links are inert text unless a later safe feature explicitly validates them.

Raw-response troubleshooting retention, if later enabled, requires encryption, narrow operator access, owner awareness where appropriate, bounded duration, access events, deletion verification, exclusion from routine backups/portable archives by default, and no use as authority.

## Cost, Rate, and Usage Controls

Version 1 enforces server-side bounded controls for:

- context/request bytes or characters;
- source count and excerpt size;
- provider input/output tokens or equivalent units;
- maximum output size;
- concurrent AI Jobs per Workspace;
- requests per time window;
- automatic retry/attempt budget;
- cost/usage budget where provider metadata permits;
- provider timeout; and
- retained Suggestion/raw-response size/count.

Limits are checked before retrieval, before transmission, while parsing response, and before retry. Exceeding a limit fails visibly and leaves authoritative content unchanged.

Usage/cost records are bounded operational evidence associated with Request/Job/provider/model. Provider figures may be delayed/estimated and are not billing authority unless reconciled.

One failing/expensive Request cannot monopolize workers or block local authoring. Rate-limit/provider outage returns privacy-safe status and uses bounded retry-wait.

Exact limits, currencies, token normalization, budget windows, alerts, and UI remain later decisions.

## Failure and Ambiguous Outcomes

Failure categories include authorization, invalid/stale context, limit, provider unavailable, known-not-sent network failure, timeout after possible send, rate limit, provider rejection, malformed/oversized response, parse/schema error, safety refusal, cancellation, local persistence failure, lease loss, and deployment shutdown.

All failures preserve authoritative Scene/Revision content.

Known-not-sent transient failures may retry within budget. Known provider failure retries only if classified transient. Malformed/safety/validation/permanent failures are terminal. Stale source triggers refresh/regeneration, not retry.

Ambiguous provider outcome is recorded/quarantined. The worker reconciles provider request/receipt/status or waits for safe evidence. It does not blindly resubmit a billable request. Duplicate valid responses map through local idempotency and do not create duplicate authoritative effects.

Provider-known success followed by local Suggestion persistence failure requires reconciliation/re-fetch where supported or bounded failure evidence; it does not trigger automatic authoritative mutation.

If response parsing partly succeeds, Version 1 does not retain partial Suggestion as complete. It may retain bounded diagnostic status or protected raw response temporarily under policy.

Ordinary workspace use remains available when AI fails. The AI provider is never a dependency for reading/editing/exporting/backing up authoritative content.

## Restore and Recovery Reconciliation

Database/structured-archive recovery follows ADR-0009 and ADR-0010.

- Unfinished AI Requests/Jobs/Attempts/effects are quarantined.
- Prior leases/worker ownership are invalidated.
- Provider credentials/sessions are not restored from portable archives and are reconfigured separately.
- Provider request IDs/effect evidence are preserved as bounded references when needed for reconciliation.
- Unknown submissions are reconciled before retry.
- Completed Suggestions may be restored under archive/retention policy but remain non-authoritative.
- Restored Suggestions are reauthorized, source-ID/hash checked, and compared with current Revision before review/application.
- Applied Revisions/Mutation Operations remain authoritative even if source Suggestion/raw response was later deleted.
- Cross-Workspace import does not preserve source Grants/provider authority and assigns new target IDs/mappings under import rules.
- Derived/operational AI caches can be rebuilt/discarded.
- No restored Job resumes or provider call repeats blindly.

Point-in-time recovery may restore local state before a provider response/effect that occurred later. Reconciliation uses provider IDs/evidence where available and owner review where not.

Restoration must not activate provider secrets, expand context, apply Suggestions, or mark content approved/Canon. Recovery events contain no manuscript/prompt/response bodies.

## Retention and Deletion

Retention categories are separate:

- AI Request metadata/context hashes for provenance/troubleshooting;
- Job/Attempt/Idempotency/effect evidence under ADR-0010;
- normalized Suggestions and review/disposition state;
- usage/cost evidence;
- transient full request/context material;
- raw provider responses if temporarily retained;
- applied Mutation Operation/Scene Revision provenance; and
- security events.

Full prompts/context copies and raw responses are not retained indefinitely by default. Normalize useful output into Suggestion and retain stable source/template/configuration hashes/references.

Rejected, expired, cancelled, failed, unapplied, and applied Suggestions may have different bounded retention based on owner recovery, provenance, troubleshooting, privacy, and archive requirements. Exact durations remain later policy.

Deletion rules:

- deleting Request/Job/Attempt/raw response cannot cascade to Suggestion or authoritative Revision/Operation if still required;
- deleting a Suggestion cannot delete an applied Revision/Mutation Operation;
- applied provenance may keep a bounded tombstone/reference even after Suggestion text deletion;
- provider-side deletion is requested/recorded where supported but cannot be guaranteed beyond provider terms;
- cleanup is authorized, Workspace-scoped, idempotent, and privacy-safe; and
- retained backups/archives may contain records until expiry under ADR-0009.

Retention minimization must not erase enough evidence to distinguish AI-assisted content, reconcile ambiguous billing/effects, or prevent unsafe idempotency replay.

## Django Application Boundary

Django services own task registry, context selection/manifest authorization, source loading, prompt-template/configuration versioning, Request/Suggestion state, Job dispatch, idempotency, provider adapter invocation boundary, response normalization, review/disposition, staleness, and application.

Workers use the same services under bounded service context. They do not query arbitrary Workspace content, write Scene revisions directly, or approve Suggestions.

The provider adapter is infrastructure behind a provider-neutral interface. Provider-specific request/response types do not leak into Scene, Revision, Suggestion disposition, Mutation Operation, or application authorization.

Applying a Suggestion always routes through ordinary Scene mutation services. Django template/rendering/output-encoding rules treat Suggestions as untrusted text.

No models, migrations, views, APIs, Jobs, adapters, prompts, or packages are created by this ADR.

## PostgreSQL Boundary

PostgreSQL will eventually store durable AI Request, Suggestion, source-reference/manifest metadata, bounded usage/effect references, and their relationships to Workspace, Scene, Revision, Job, Idempotency, Mutation Operation, and Account.

Constraints should reinforce:

- stable UUID uniqueness;
- direct Workspace consistency;
- valid Request/Suggestion states/dispositions;
- source/target/reference integrity;
- bounded output/configuration versions;
- unique idempotency scopes through ADR-0010;
- protective deletion for applied provenance;
- no cross-Workspace Suggestion application; and
- result/application reference consistency where row-local.

Database constraints cannot authorize an Account, assess Canon, prove provider truth, detect every stale source, parse untrusted output, or decide approval. Django services do.

Raw provider bodies, full prompts, credentials, and secrets are not placed in ordinary operational columns by default. If bounded encrypted raw retention is later selected, storage/schema/key boundaries require separate review.

Exact tables, fields, indexes, constraint names, JSON usage, encryption, and retention partitions remain later physical-schema work.

## Rationale

A server-only provider-neutral adapter keeps secrets and policy out of the browser and prevents vendor schemas from becoming the domain model.

Distinct staged Suggestions preserve human authority: provider output can be reviewed, rejected, edited, or applied without overwriting source material. Ordinary Scene concurrency prevents stale Suggestions from destroying newer work.

Exact source Revision IDs/hashes provide explainable context, staleness detection, reproducibility evidence, and recovery verification without retaining full prompts in operational logs.

ADR-0010 Jobs/idempotency/reconciliation handle provider latency and uncertain outcomes honestly. Short transactions isolate provider failure from PostgreSQL and ordinary authoring.

Normalized provider-neutral Suggestions plus bounded metadata enable provider changes while preserving provenance. Data minimization and bounded retention reduce exposure of unpublished manuscripts.

## Decision Criteria

Options are evaluated against:

1. explicit human authority and no automatic Canon/application;
2. server-side authorization, Workspace isolation, and secret protection;
3. exact context-source provenance and stale detection;
4. immutable Scene revision/concurrency invariants;
5. provider failure/timeout/duplicate/retry correctness;
6. privacy/data minimization and safe rendering;
7. provider/model portability without equivalence claims;
8. bounded cost/rate/usage;
9. restoration/quarantine and auditability;
10. maintainability for one narrow Version 1 capability;
11. separation of domain, operational, provenance, security, and provider records;
12. owner-controlled retention/deletion; and
13. future extensibility without autonomous agency.

## Alternatives Considered

### Direct provider calls from browser

Rejected. It exposes credentials/policy/context construction, trusts client limits/authorization, complicates logging and provider portability, and repeats Story Engine weaknesses.

### Server-side provider calls

Selected through the AI adapter with bounded Jobs and source authorization.

### Synchronous AI only

Simple status but vulnerable to request timeouts, provider latency, retries, cancellation, and ambiguous outcomes. Rejected as the primary model; trivial local preparation may be synchronous.

### Background AI Jobs

Selected using ADR-0010.

### Store raw provider responses only

Rejected. Provider schemas are unstable/untrusted, hard to render/port, and encourage domain coupling.

### Normalized AI Suggestion records

Selected. Raw retention is optional short troubleshooting evidence, not authority.

### Write provider output directly into Scene

Rejected because it bypasses human review, concurrency, immutable history, normalization, and provenance.

### Explicit human approval

Selected before every authoritative application.

### Automatic application

Rejected for Version 1.

### Full-response acceptance

Allowed only as explicit owner-reviewed complete proposed content through ordinary save.

### Partial acceptance

Allowed as explicit human selection/editing, never automatic merge.

### Regenerate on stale source

Preferred simple path: new Request/current context/provenance.

### Apply despite stale source

Rejected as direct action. Owner may manually derive/edit a new proposal against current state.

### Provider-specific schema

Rejected for core Request/Suggestion/domain records. Provider metadata remains bounded adapter evidence.

### Provider-neutral adapter

Selected.

### One narrow capability

Selected for V1 to bound privacy, prompts, output, tests, and cost.

### Broad agent framework

Rejected: tool authority, autonomous steps, broad context, failure/recovery, and cost exceed scope.

### Full prompt retention

Rejected by default due to manuscript duplication/privacy. Exceptional bounded encrypted troubleshooting retention requires later approval.

### Template hashes, source references, and bounded configuration

Selected baseline for provenance/debugging.

### Indefinite response retention

Rejected due to privacy/storage/provider-copy duplication.

### Bounded retention

Selected with category-specific later durations.

### Provider idempotency only

Rejected because provider scope/retention/semantics do not protect local duplicate delivery/authorization.

### Local idempotency plus provider support

Selected.

### Blind retry

Rejected after ambiguous outcomes.

### Reconciliation after ambiguous outcome

Selected.

### Include provider secrets in backups

Rejected for structured archives/ordinary backups; use separate secret recovery/rotation.

### Separate secret recovery

Selected.

### Restore unfinished AI Jobs

Rejected as blind resume.

### Quarantine restored work

Selected with reconciliation/reauthorization.

## Comparative Assessment

### Provider access strategy

| Strategy | Secret safety | Authorization | Portability | Decision |
| --- | --- | --- | --- | --- |
| Browser direct | Weak | Client-exposed | Low | Rejected |
| Server provider-specific calls everywhere | Stronger | Server | Low | Rejected architecture |
| Server neutral adapter | Strong | Central | Strong | Selected |

### Output persistence strategy

| Strategy | Review | Portability | Safety | Decision |
| --- | --- | --- | --- | --- |
| Direct Scene write | None/bypass | Low | Poor | Rejected |
| Raw response only | Possible | Low | Provider-coupled | Rejected core |
| Normalized Suggestion | Explicit | Strong | Staged/untrusted | Selected |
| No persistence | Ephemeral | Moderate | Weak provenance/recovery | Not selected |

### Human-approval strategy

| Strategy | Author control | Concurrency | Decision |
| --- | --- | --- | --- |
| Automatic apply | Weak | Often bypassed | Rejected |
| Worker marks approved | Weak | Wrong authority | Rejected |
| Human apply through Scene service | Strong | Full token checks | Selected |
| Human apply + automatic Canon | Incomplete control | Separate concern blurred | Rejected |

### Stale-source handling

| Strategy | Lost-work risk | Provenance clarity | Decision |
| --- | --- | --- | --- |
| Silent apply | High | Poor | Rejected |
| Automatic merge | High/complex | Ambiguous | Rejected V1 |
| Force apply | High | Explicit but unsafe | Rejected direct path |
| Warn/block, compare/edit/regenerate | Lowest | Strong | Selected |

### Retry and ambiguous-outcome behavior

| Strategy | Duplicate cost/effect | Evidence | Decision |
| --- | --- | --- | --- |
| Blind retry | High | Weak | Rejected |
| Provider key only | Reduced/provider-dependent | Moderate | Insufficient |
| Local + provider idempotency | Lower | Strong | Selected |
| Reconcile ambiguous before retry | Lowest practical | Strongest | Selected |

### Prompt/context retention

| Strategy | Debuggability | Privacy | Decision |
| --- | --- | --- | --- |
| Full indefinite prompts | Strong | Poor | Rejected |
| No provenance | Weak | Strong | Insufficient |
| Template/config/source refs+hashes | Strong enough | Strong | Selected |
| Short encrypted raw retention | Strong | Controlled risk | Optional later |

### Provider portability

| Strategy | Vendor coupling | Migration | Output equivalence | Decision |
| --- | --- | --- | --- | --- |
| Provider-native records | High | Hard | N/A | Rejected core |
| Neutral Request/Suggestion + adapter | Low | Manageable | Not promised | Selected |
| Multi-provider agents | High complexity | Hard | Not promised | Out of scope |

### Retention strategy

| Strategy | Provenance | Privacy/storage | Decision |
| --- | --- | --- | --- |
| Delete immediately | Weak | Strong | Insufficient |
| Retain everything indefinitely | Strong | Poor | Rejected |
| Bounded category-specific retention | Strong enough | Controlled | Selected |
| Raw-only retention | Provider-coupled | Poor | Rejected |

## Evidence

### Repository evidence

- Product vision/principles state AI assists and the author decides; output never becomes Canon automatically; context is deliberate and privacy is default.
- Version 1 scope permits one narrow explicitly invoked AI capability with visible sources, staged output, provenance, and unchanged source on failure.
- Architecture overview defines an AI gateway, bounded Jobs, external provider trust boundary, and non-authoritative output.
- AI-context architecture selects scene-focused review, manifest-driven exact sources, provider-neutral construction, no tools, prompt-injection resistance, and bounded retention.
- Security/integration architectures require server-side secrets, least privilege, output validation, provider portability, no direct Workspace access, and safe retries.
- ADR-0001 through ADR-0010 establish trust, Django/PostgreSQL, revision/concurrency, authentication, content, schema, recovery, and Job/idempotency/reconciliation invariants.
- Architecture handoff preserves the same non-authoritative AI and implementation-deferred boundaries.
- Story Engine audit shows direct client provider calls, credentials/settings mixing, broad fallback context, provider-specific prompts, and direct generated-content application as patterns to reject.

### Provider-neutral security/privacy guidance reviewed conceptually

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html)
- [OWASP Cross Site Scripting Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)
- [OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)

These support deny-by-default authorization, server-side secret custody, minimal logging, untrusted output handling, safe rendering, endpoint/network restrictions, resource limits, and privacy-conscious errors.

### Evidence still required

Before implementation:

- confirm the exact scene-focused review user journey/output contract;
- evaluate provider privacy/retention/training/human-review/subprocessor/region/incident terms;
- define provider-neutral Request/Suggestion/context-manifest schemas;
- define source hashing/canonicalization without duplicating content;
- select prompt-template/configuration versioning and preview behavior;
- define response validation/normalization and untrusted-rendering rules;
- decide whether any encrypted raw-response retention is necessary;
- define Suggestion dispositions, human-edit/partial-apply provenance, and deletion/tombstones;
- define staleness UX and comparison/regeneration;
- set request/token/cost/rate/concurrency/retry/retention limits;
- define provider effect/idempotency/reconciliation adapter contract;
- define secret delivery/rotation/revocation and provider outage behavior;
- define restore/archive inclusion and Job quarantine;
- test prompt injection/context escape/malformed output/ambiguous outcome; and
- use synthetic content/provider fixtures only.

## Consequences

### Positive

- Provider secrets/policy stay out of the browser.
- Provider output cannot overwrite manuscripts automatically.
- Suggestions preserve clear AI origin and human review.
- Exact source revisions make staleness and provenance explainable.
- Ordinary Scene transactions preserve immutable history and conflicts.
- Provider changes do not require changing the domain model.
- Job/idempotency/reconciliation handles latency and ambiguity honestly.
- Minimal operational records reduce manuscript duplication/leakage.
- Provider outage does not block local authoring.
- Recovery cannot blindly resume provider calls or apply Suggestions.

### Negative

- Request, Suggestion, context, Job, effect, and application records add schema/workflow complexity.
- Human approval adds steps compared with direct generation into the editor.
- Stale Suggestions may be unusable without regeneration/editing.
- Provider-neutral normalization can hide provider-specific features.
- Bounded/no raw-response retention makes some debugging harder.
- Exact context hashing/versioning requires careful canonicalization.
- External provider processing remains a privacy exposure.
- Usage/cost/rate controls require provider-specific translation.
- Partial acceptance provenance and UI are nontrivial.
- Ambiguous outcome reconciliation can delay results and require manual review.

### Neutral or Operational

- Model output equivalence across providers is not promised.
- Exact provider/model/prompt/output schema remains later work.
- Suggestions may be archived/backed up under later retention policy.
- Applied content remains durable without the provider.
- Tool/agent/retrieval features require later ADRs.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Browser exposes provider credential | Provider/archive compromise | Server-only adapter, secret isolation | Server compromise remains |
| Context includes unrelated content | Privacy/spoiler leak | Manifest, exact sources, limits, execution revalidation | Selection bugs remain possible |
| Prompt injection expands authority | Secret/tool/data exposure | No tools/retrieval, delimit sources, server policy, output untrusted | Model may still emit manipulative text |
| Provider output writes directly | Lost author control | Staged Suggestion and human apply only | UI bugs could misrepresent state |
| Stale Suggestion overwrites Scene | Lost work | Source hashes + current token + no force/merge | Manual copied text may still be inappropriate |
| Provider timeout retried blindly | Duplicate charge/output | Effect evidence/idempotency/reconciliation | Provider may lack status support |
| Raw responses retained too long | Manuscript/privacy exposure | Default transient; bounded encrypted optional retention | Provider retains its own copy |
| No raw response impedes debugging | Hard incident diagnosis | Template/source/config hashes and bounded status | Some provider defects unreproducible |
| Provider-specific schema leaks inward | Lock-in/migration cost | Neutral adapter/normalized Suggestion | Unique features may be unavailable |
| Cost runaway/retry storm | Expense/availability | Budgets, rate/concurrency/output/retry limits | Provider usage reporting may lag |
| AI Suggestion mistaken for Canon | Creative-authority error | Visible state, separate application/Canon actions | UI wording remains critical |
| Partial acceptance becomes auto merge | Hidden overwrite | Explicit author-edited complete proposal | UX implementation risk |
| Output contains scripts/URLs/code | XSS/SSRF/execution | Escape, inert rendering, no execution/tools | Human may copy unsafe instructions elsewhere |
| Logs leak prompts/content | Privacy breach | Allowlisted metadata, tests, no bodies/titles | Debug misconfiguration can regress |
| Restore resumes AI Jobs | Duplicate provider effects | Quarantine and reconcile | Manual recovery effort |
| Restored Suggestion applied blindly | Stale/unauthorized mutation | Reauthorize/source/current checks | Long-lived Suggestions often stale |
| Suggestion deletion erases provenance | Unexplained applied content | Applied Revision/Operation retain bounded tombstone | Less detail after privacy deletion |
| Provider secret included in archive | Credential compromise | Explicit exclusion/scanning/separate recovery | Future fields can regress |
| Provider outage blocks product | Lost availability | AI isolated/optional; local workflow independent | AI feature unavailable |
| Provider terms change | Privacy/compliance risk | Provider review, replaceable adapter, disable capability | Previously processed data may persist |

## Security and Privacy Review

- Security-sensitive: Yes; AI transmits private manuscript context to an external processor.
- Primary references: `docs/architecture/security.md`, `docs/architecture/ai-context.md`, ADR-0001 through ADR-0010.
- Additional references: product docs, integrations, data model, architecture handoff, and Story Engine audit.

### Assets and trust boundaries

Assets include manuscripts, source revisions/hashes, context manifests, prompts, Suggestions, provider credentials, usage/cost, Jobs/effects, review/application actions, and provenance. Browser, provider, provider subprocessors, networks, worker environment, raw-response storage, and restored artifacts cross trust boundaries.

### Authorization and agency

Only Django determines source access, task scope, review, and application. Provider IDs/content and worker/service identity convey no authority. AI has no tools, browse/file/database access, autonomous multi-step control, or ability to approve/apply/Canonize.

### Data minimization and provider privacy

Send only task-specific approved sources. Provider selection must evaluate retention/training/human review/geography/subprocessors/deletion/security terms. Context preview and provenance explain included sources without exposing them in logs.

### Secret and network security

Credentials are server-side, least-privileged, rotated/revocable, never client-visible or archived. Outbound access uses approved endpoints, authenticated transport, timeouts, response limits, redirect/SSRF protection, and no response-driven follow-up URLs.

### Output/injection safety

Provider responses are untrusted text. Validate size/schema, escape rendering, prohibit unsafe HTML/code execution/evaluation, and treat embedded instructions as content. Applying text still uses ordinary validation/normalization/concurrency.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- browser inability to access credentials/provider directly;
- every Request/source/Suggestion/review/apply Workspace authorization boundary;
- exact preview/manifest/source/request agreement;
- source changes before submission and application;
- prompt injection attempting context expansion/tools/secrets/policy change;
- request/response limits and malformed/hostile output;
- safe rendering of HTML/Markdown/code/URLs/paths;
- duplicate Job delivery/local/provider idempotency;
- timeout before/after send, known/unknown outcomes, reconciliation, no blind retry;
- cancellation before/after send;
- Suggestion stage/reject/retain/expire/delete/full/partial/human-edit flows;
- ordinary apply transaction, stale conflict, rollback, provenance, no automatic Canon;
- usage/cost/rate/concurrency/retry limits;
- secret/prompt/content/title absence from Jobs/logs/metrics/errors/archives;
- provider outage with local workspace availability;
- restore quarantine and restored Suggestion staleness/authorization; and
- retention/deletion/tombstone behavior without authoritative cascade.

### Residual risk

The provider necessarily sees selected plaintext context and may retain/process it under external terms. A compromised server/worker/provider can expose it. Models can generate misleading, offensive, copyrighted, insecure, or manipulative text. Human approval reduces but does not eliminate judgment errors. Hashes/metadata may reveal sensitive patterns. Provider billing/status evidence may be incomplete.

## Product and Architecture Alignment

### Product alignment

The decision implements “AI assists; the author decides,” preserves explicit content states/provenance, keeps context deliberate, protects privacy, and prevents provider lock-in from becoming archive lock-in.

### Scope alignment

It supports one narrow scene-focused review capability. It excludes autonomous writing, general agents, broad retrieval, embeddings, vector search, tool use, external browsing, and background source modification.

### ADR alignment

- ADR-0001: browser/provider remain outside policy/authority boundary.
- ADR-0002: Django modular monolith hosts the gateway/services.
- ADR-0003: PostgreSQL stores authoritative/supporting records; provider is not storage.
- ADR-0004: application uses Scene concurrency/idempotency and immutable revisions.
- ADR-0005: Account, service identity, human approval, and recent/current authorization remain distinct.
- ADR-0006: normalized plain text/source revision identity guides context/application.
- ADR-0007: Suggestion/supporting records remain separate from creative domain/provenance/security.
- ADR-0008: UUID/Workspace/Mutation Operation/constraints guide future schema.
- ADR-0009: archives exclude secrets; restoration preserves non-authoritative Suggestions without activation.
- ADR-0010: AI uses durable Jobs/Attempts/Idempotency/effects/retry/cancellation/quarantine.

### Architecture alignment

The model matches explicit invocation, context manifests, server retrieval, provider-neutral gateway, staged Suggestions, safe failure, privacy-conscious logging, and portable recovery.

### Normative-document impact

If accepted, AI-context, security, data-model, integration, backup/archive, and job documents should be reconciled with Request/Suggestion/source-staleness/application/retention boundaries. The ADR index should be updated. No implementation is authorized by this decision.

## Migration and Portability

Provider-neutral Request/Suggestion records preserve task/source/template/output/provenance meaning independently of provider-native response schemas. Provider/model IDs remain external metadata.

Changing provider/model creates new Requests/Suggestions; it does not rewrite old records or imply equivalent outputs. Existing applied Scene Revisions remain usable without any provider.

Schema migrations preserve Request/Suggestion UUIDs, Workspace/source references/hashes, dispositions, applied Revision/Operation links, provider metadata, usage, and retention/tombstones.

Structured archives may include Suggestions/Request provenance under retention policy, excluding secrets/raw responses by default. Same-archive restoration preserves IDs but does not resume Jobs or authorize application. Cross-Workspace import assigns new target identities/mappings and no source Grants/provider authority.

Provider disconnection/revocation leaves authoritative archive and applied revisions intact. Pending work fails/quarantines safely.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Finalize the single scene-focused review task/user journey.
- [ ] Define provider-neutral context-manifest, AI Request, Suggestion, source-reference, output, usage, and disposition schemas.
- [ ] Define prompt-template/configuration versioning and deterministic request construction.
- [ ] Define source content hashing/canonicalization and stale comparison.
- [ ] Define full/partial/human-edited application UX/provenance.
- [ ] Define response validation/normalization and safe rendering.
- [ ] Decide whether bounded encrypted raw-response retention is necessary.
- [ ] Evaluate provider privacy/security/retention/training/human-review/subprocessor/region/incident terms.
- [ ] Define provider adapter effect/idempotency/receipt/reconciliation contract.
- [ ] Define server-side secret delivery, rotation, revocation, and outage behavior.
- [ ] Set bounded request/output/context/token/cost/rate/concurrency/retry/retention policies.
- [ ] Define Job type/payload/retry/cancellation/quarantine under ADR-0010.
- [ ] Define restore/archive inclusion and cross-Workspace import mapping.
- [ ] Add later unit/integration/adversarial/provider-fixture/job/concurrency/retention/restore tests using synthetic content.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes application code, Django initialization, models, migrations, Jobs, adapters, providers, prompts, credentials, secrets, packages, database objects, tests, sample manuscripts, tool use, agents, browsing, file access, embeddings, retrieval systems, deployment, modification of the old Story Engine, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No application code, model, migration, Job, provider integration, prompt, secret, test, package, database object, deployment configuration, sample manuscript, vendor, model, SDK, vector database, embedding provider, agent framework, tool, retention duration, limit, or schema is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
