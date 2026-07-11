# Strange Novelty Integration Architecture

## Purpose and Scope

This document defines the Version 1 integration boundary and the constraints that any future external integration must satisfy. It establishes provider-independent rules for authorization, data movement, identity, provenance, synchronization, failure, security, portability, and recovery.

Version 1 includes no external document, storage, email, publishing, or synchronization integration. The core authoring workflow must be fully usable without one. This document does not add an integration to Version 1 scope and does not select a vendor, protocol, SDK, provider, or implementation framework.

The authoritative creative archive remains inside Strange Novelty. External services may later extend a demonstrated workflow, but they remain replaceable, disconnectable, and subordinate to the author-controlled Workspace.

## Integration Design Goals

Future integrations should:

- address a documented author workflow rather than provide general external access;
- preserve privacy, authorial authority, content states, provenance, and contextual Canon;
- request the narrowest authority and data scope needed for the approved workflow;
- define every inbound and outbound data flow before implementation;
- keep Strange Novelty independently usable and authoritative;
- prevent remote errors, conflicts, or deletions from silently damaging local content;
- make external origin, synchronization state, and unresolved conflicts visible;
- tolerate provider outages, throttling, revocation, and partial failure;
- support disconnection, export, backup, restoration, and migration without provider dependence; and
- remain understandable and operable for one author without enterprise administration.

## Core Principles

### The archive remains local and authoritative

Strange Novelty is the authoritative archive for its records, states, provenance, and revision history. No external copy is the only copy of a manuscript, artwork item, metadata record, provenance event, export, or backup.

### Authorization is explicit and narrow

The author deliberately connects each integration and approves its documented purpose. Read, write, delete, publish, and administrative permissions are distinct. Broad account-wide authority is not acceptable merely because it simplifies implementation.

### External systems are untrusted boundaries

Provider identities, content, callbacks, metadata, and status are untrusted input. Familiar ownership or brand does not move a provider inside the application trust boundary.

### External content preserves its origin

Imported or synchronized material retains external provenance and does not become Canon automatically. Provider location, ownership, or successful synchronization does not establish creative authority.

### Failure is contained

Integration failure affects the integration workflow, not ordinary local authoring, navigation, search, export, backup, or restoration. Ambiguous outcomes remain visible and are reconciled rather than guessed.

### Disconnection is a normal lifecycle event

An integration can expire, be revoked, be removed by the provider, or be deliberately disconnected. The core archive remains usable and understandable afterward.

## Version 1 Integration Scope

Version 1 has no external integration capability. It does not require an external service for authentication of creative-content access, authoring, search, AI context retrieval, export, backup, or restoration.

Version 1 architecture work is limited to defining:

- the adapter boundary future integrations must use;
- the authority and data-flow constraints adapters must obey;
- provider-independent identity, provenance, synchronization, and failure concepts;
- security, privacy, portability, backup, and restoration invariants; and
- the decisions and tests required before a future integration enters scope.

An AI provider used through the separately defined AI gateway is an external trust boundary, but it is governed by the AI context architecture rather than treated as a general integration adapter. The AI provider receives one bounded request and no Workspace access.

## Explicitly Excluded Version 1 Integrations

Version 1 excludes:

- cloud-drive browsing, import, export, or synchronization;
- online-document editing or synchronization;
- email reading, sending, attachment import, or mailbox access;
- publishing, submission, social, or public-sharing services;
- external artwork, map, media, or research libraries;
- calendar, task, note, source-control, or project-management services;
- general webhooks, automation platforms, plugins, or user-defined connectors;
- external search, indexing, semantic retrieval, or vector services acting on the Workspace;
- provider-hosted primary manuscripts or backups;
- bidirectional synchronization of creative records; and
- any account-wide integration permission grant.

Mention in the product vision or roadmap does not authorize implementation. A future integration requires approved scope, a documented workflow, completed security and privacy review, acceptance criteria, and any necessary decision records.

## Trust Boundaries

### Browser boundary

The browser may initiate connection, display consent, and show integration state. It is not trusted to define permission scope, authorize records, hold provider secrets, or decide synchronization effects. Server-side code revalidates the owner session, Workspace, adapter, requested action, provider grant, and affected records.

### Application-server boundary

The application server is the policy enforcement point. It authorizes integration actions, validates inbound data, applies domain and concurrency rules, records provenance, and delegates bounded work. An adapter cannot bypass it to write authoritative records.

### Adapter boundary

Each integration adapter is a constrained translator between one approved external workflow and provider-independent application operations. It receives only the authority, records, and secrets required for that operation.

### Provider boundary

Every provider, including one controlled by the author, remains outside the private application boundary. Provider availability, permissions, identities, content, timestamps, change markers, callbacks, and errors are not authoritative application facts until validated.

### Background-job boundary

Synchronization and transfer jobs are separate principals. A job has a bounded Workspace, adapter, operation, data scope, direction, and credential reference. It does not inherit unrestricted owner, database, storage, export, backup, AI, or administrative authority.

### Storage and operational boundary

Integration credentials, mappings, cursors, staged content, conflicts, and audit records are protected application data. Operational logs and telemetry are separate and must not contain transferred creative bodies or secret values.

## Integration Adapter Boundary

Every future integration must use a dedicated adapter behind the application server. Direct provider logic must not spread through domain records, browser code, background jobs, or core authoring modules.

An adapter is responsible for:

- translating an approved provider-independent operation into bounded provider requests;
- using only the grant and resource scope approved for that integration instance;
- validating provider responses, callbacks, identifiers, pagination, limits, and errors;
- normalizing external records without assigning local authority;
- maintaining external-identifier mappings and synchronization cursors where required;
- returning staged changes, status, and conflicts to application-controlled workflows;
- supporting cancellation, retry, reconciliation, revocation, and disconnection; and
- preventing provider-specific fields from becoming the primary identity or source of truth for local records.

An adapter must not receive unrestricted Workspace, database, filesystem, object-storage, search, export, backup, AI, integration, or administrative access. New capabilities are denied until explicitly designed and authorized.

## Authorization and Consent

- Only the authenticated owner may connect, reauthorize, change, or disconnect an integration.
- The application must describe the integration’s purpose, provider-facing identity, requested permissions, accessed resource scope, data directions, retention, and expected effects before authorization.
- Consent applies to one named integration instance and documented workflow, not to unspecified future features.
- Expanding permissions, resource scope, data direction, or destructive capability requires fresh explicit consent.
- Server-side authorization is required for every import, synchronization, outbound write, deletion request, publish action, and administrative change.
- High-impact actions may require recent authentication when justified by the security policy.
- Consent, grant changes, reauthorization, revocation, and disconnection create privacy-conscious audit records.
- A provider authorization screen does not replace Strange Novelty’s own explanation and server-side policy checks.

Authorization failures must fail closed and must not reveal unrelated private records or provider resources.

## Least-Privilege Permissions

Each integration must request the narrowest available combination of:

- provider account or tenant;
- specific resource, folder, document, mailbox, label, project, or collection;
- operation type;
- data fields;
- duration; and
- user or service identity.

Read, create, update, delete, publish, share, permission-management, billing, and administrative permissions remain distinct. A read-only import must not request write access. A document update must not imply deletion, sharing, or account administration. A publishing workflow must not receive general archive access.

If a provider cannot offer sufficiently narrow permissions, the limitation must be documented and explicitly accepted before the integration can enter scope. Broad account-wide access must not be requested for implementation convenience or future possibilities.

## Credential and Token Handling

- Provider credentials and tokens remain server-side.
- They must never be committed to Git, embedded in client bundles, written to URLs, copied into manifests or provenance, or exposed to routine logs, analytics, traces, errors, exports, and backups.
- Browser exposure is limited to an approved provider-controlled authorization flow and non-secret state needed to complete it.
- Authorization responses require server-generated state binding, expiration, and validation against the initiating session and integration instance.
- Tokens are stored with strong protection, separately scoped by environment and integration instance, and accessible only to components that need them.
- Access and refresh credentials, webhook secrets, client credentials, signing keys, and administrative credentials are treated as distinct secrets.
- Expiration, rotation, refresh, revocation, provider-side invalidation, and suspected compromise require documented handling.
- Refresh failure must not trigger an infinite loop or silently broaden permissions.
- Disconnecting revokes provider grants where supported and removes or disables local credential material according to retention policy.

The final authorization protocol, token format, secret manager, and provider are undecided.

## Data-Flow Direction

Every integration capability must declare one of these directions for each record or operation:

- **Inbound import:** provider to staged Strange Novelty content.
- **Outbound copy:** Strange Novelty to a provider-controlled destination.
- **Inbound synchronization:** provider changes are proposed against an established mapping.
- **Outbound synchronization:** approved Strange Novelty changes are proposed remotely.
- **Bidirectional synchronization:** independently editable copies exchange changes under explicit conflict rules.
- **Action-only:** a bounded external action occurs without establishing synchronized content.

Direction is defined per workflow, not assumed for an entire provider. Read permission does not imply import; write permission does not imply continuous synchronization. Bidirectional synchronization has the highest ambiguity and risk and requires specific justification before entering scope.

The interface must let the author understand what leaves Strange Novelty, what enters it, what may change remotely, and what remains local.

## Source-of-Truth Rules

The authoritative archive for Strange Novelty records remains inside Strange Novelty.

For each mapped field or artifact, an integration design must state:

- whether the external copy is an import source, export destination, working copy, publication output, or synchronized replica;
- which side may initiate changes;
- which side is authoritative when values differ;
- whether a remote value can update local staged or authoritative content;
- how author approval is represented; and
- how the mapping ends on disconnection.

Provider timestamps, revision numbers, and successful responses inform reconciliation but do not replace local identity, state, provenance, or approval. No integration may make the external service the only recoverable source of manuscripts, artwork, metadata, provenance, or backups.

## Import and Synchronization Semantics

### Import

Inbound data enters a staging boundary. It is parsed, validated, assigned imported provenance and Imported content state, and presented for review before it can become authoritative application content. Import does not overwrite by name, infer Canon, erase local history, or conceal partial results.

### Synchronization

Synchronization requires an explicit mapping between stable local identity and provider identity, a defined base version on both sides, and a recorded direction. Each cycle discovers changes, validates them, stages or proposes effects, detects conflicts, and records a bounded outcome.

Imported and synchronized material must follow normal validation, content-state, provenance, ownership, concurrency, link, revision, and review rules. Provider success does not bypass application transactions or author approval. Continuous polling or callback-driven synchronization must remain bounded and disableable.

### Deletion

Remote deletion is a synchronization observation, not permission to purge local content. Depending on the approved workflow it may mark the external mapping missing, create a conflict, pause synchronization, or propose an explicit local lifecycle action. Permanent local purge always requires separate protected author intent.

Local deletion does not imply remote deletion unless that behavior and permission were explicitly approved. Existing backups may retain prior copies according to their retention policy.

## Conflict Handling

A conflict exists when both sides changed from a known base, identities are ambiguous, a remote deletion competes with local change, the provider state cannot be reconciled, or applying a change would violate local rules.

Conflicts must:

- be detected before silent overwrite;
- identify the mapped record, direction, known base, and changed sides without exposing unnecessary content in logs;
- preserve local authoritative content and external provenance;
- pause the affected item or operation rather than the entire local application where practical;
- present understandable choices to the author;
- require explicit resolution when creative meaning, deletion, state, or authority is affected; and
- record the decision and resulting versions.

Automatic last-write-wins is prohibited. Automatic text merge may be offered only after a later approved design and must remain reviewable. A provider timestamp alone cannot resolve a conflict.

## Idempotency and Retries

Integration operations must be safe under network interruption, duplicate delivery, job restart, callback replay, and provider timeout.

- Each externally visible operation uses a stable operation identifier or provider-supported idempotency mechanism where available.
- Local state distinguishes planned, submitted, acknowledged, completed, failed, outcome-unknown, cancelled, and reconciled operations.
- Retries reuse the same logical operation when safe and do not create duplicate local records, remote copies, messages, publications, or destructive actions.
- An unknown provider outcome is reconciled before retry when duplication would matter.
- Retry policy uses bounded attempts, backoff, jitter where appropriate, and provider guidance.
- Permanent authorization, validation, policy, or conflict errors are not retried automatically.
- Retry never broadens permission or data scope.

Idempotency does not make a destructive or publishing operation safe without explicit authorization and reconciliation.

## Partial Failure

Batch and multi-step operations must assume partial failure. Before implementation, each workflow defines:

- its atomic unit;
- which steps are locally transactional;
- which external effects cannot be rolled back;
- how completed and failed items are identified;
- how resumable state is recorded;
- how duplicates are prevented;
- which compensating action is safe; and
- what the author sees and can do next.

Partial success must not be reported as complete success. Successful items retain their provenance; failed items remain retryable or reviewable without discarding the batch record. A compensating delete or overwrite requires the same permission and safety review as a direct action.

## Rate Limits and Quotas

Every integration must treat provider limits and local resource limits as normal operating conditions.

- Bound requests per operation, time window, integration instance, and Workspace.
- Bound records, pages, bytes, attachments, concurrency, processing time, and retained staging data.
- Respect provider throttling and retry guidance without infinite retries.
- Use pagination and cursors defensively; do not assume stable ordering or complete pages.
- Surface quota exhaustion and the affected scope without blocking local authoring.
- Prevent one failing item or provider from monopolizing background work.
- Avoid polling when no approved workflow requires it.

Quota increases must not silently expand consent, data exposure, or synchronization scope.

## Webhooks and Callbacks

Webhooks and callbacks are untrusted external input. They must:

- arrive at a dedicated bounded endpoint over protected transport;
- be authenticated using the provider’s reviewed mechanism;
- validate signatures or equivalent evidence using protected server-side secrets;
- enforce timestamp, nonce, event-identifier, or other replay protection;
- validate method, content type, schema, size, event type, provider account, and integration mapping;
- reject unknown integrations, resources, event types, and unsupported versions;
- acknowledge quickly and place bounded follow-up work on a controlled job path;
- tolerate duplicate, delayed, missing, and out-of-order delivery;
- avoid trusting payload URLs or fetching arbitrary destinations;
- record minimal status without logging sensitive payload bodies; and
- never write authoritative content or perform destructive actions solely because a callback requested it.

Callback delivery is a change signal, not authoritative proof of current provider state. When necessary, the adapter verifies current state through a narrowly authorized provider request.

## External Identifiers

Provider identifiers are not primary identity for Strange Novelty records. Local records retain stable application identifiers across rename, move, provider change, disconnection, export, backup, and restoration.

An external mapping should include:

- local Workspace and record identifier;
- integration instance and provider account scope;
- external resource type and identifier;
- mapping purpose and data direction;
- known external version, revision, cursor, or change marker;
- local base version used for synchronization;
- creation, verification, last-success, and status timestamps; and
- active, missing, conflicted, disconnected, or superseded status.

External identifiers are treated as opaque, validated values. They must not be used unsafely as paths, queries, authorization evidence, or cross-provider identity. Reuse or reassignment by a provider must be detectable where possible.

## Provenance Requirements

Integration provenance must explain origin and relevant transformation without storing secrets. Depending on the workflow it records:

- integration instance and provider type;
- external resource type and safe identifier reference;
- import or synchronization batch and operation;
- direction and source-of-truth rule;
- observed provider version and local base version;
- time observed, transferred, staged, reviewed, applied, rejected, or disconnected;
- fields or objects included and excluded at a bounded level;
- importer or adapter version;
- transformations, validation warnings, conflicts, partial failures, and retry outcomes;
- authenticated author review or approval where required; and
- resulting local records, revisions, mappings, and content states.

Credentials, tokens, webhook secrets, authorization codes, cookies, and secret-bearing provider responses never belong in provenance. Editing or reclassifying synchronized content does not erase its external origin.

## Content-State Handling

- New retained inbound content begins as Imported content unless a later approved workflow defines a more conservative staging state.
- Imported content remains distinguishable through review, edits, mapping, and synchronization.
- Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion must not be flattened into provider labels or folder locations.
- External status, publication state, revision state, or document ownership is not a Strange Novelty content state.
- Outbound copies carry state metadata only when the export contract explicitly supports it; omission does not change local state.
- Remote edits cannot promote, deprecate, restore, or broaden the Creative Context of local content automatically.
- Conflicting content states are preserved for author review rather than silently resolved.

## Canon and Authorial Authority

The author is the only human authority for creative-state changes in Version 1. No integration, remote collaborator, provider automation, synchronization success, folder placement, publication event, or external label may make content Canon.

Promotion to Canon, expansion of Canon context, replacement of authoritative material, acceptance of imported content, and restoration of deprecated authority require explicit author action through ordinary server-side state-transition rules. Integration jobs may prepare proposals but cannot infer approval.

Publishing or exporting Canon does not make the external copy authoritative over the local record. Importing a previously published artifact does not prove that it represents current Canon.

## Privacy and Data Minimization

- Each workflow transfers only the records, fields, objects, and metadata required for its stated purpose.
- The author must be able to understand which provider resources are accessed and which Strange Novelty content leaves or enters the private boundary.
- Entire Workspaces, databases, directories, backups, exports, mailboxes, drives, or account-wide collections must not be scanned by default.
- Discovery uses the narrowest provider resource scope and result limits available.
- Sensitive filenames, titles, identifiers, relationships, and metadata are minimized along with content bodies.
- Credentials, sessions, audit records, unrelated provenance, deleted content, backups, and administrative data are excluded from transfers.
- Provider retention, training use, human access, subprocessors, geographic processing, deletion, and incident terms require review before selection.
- Staged and cached external data has explicit retention and deletion rules.
- Third-party tracking or analytics embedded in an integration flow is a separate external disclosure and requires review.

## Logging and Telemetry

Routine logs, analytics, metrics, traces, error reports, and alerts must not contain:

- manuscript, note, research, email, artwork, attachment, or synchronized content bodies;
- raw provider payloads or callback bodies;
- credentials, authorization codes, tokens, cookies, secrets, or signed URLs;
- sensitive filenames, document titles, mailbox subjects, search terms, or provider URLs when a bounded reference is sufficient;
- exports, backups, database records, or AI content; or
- arbitrary exception locals, request headers, or response bodies.

Permitted operational data may include integration type, bounded operation category, non-secret correlation identifier, coarse counts, duration, attempt number, rate-limit state, and privacy-conscious error category.

Integration audit records are separate from operational logs. They preserve authorization, permission changes, synchronization decisions, conflicts, external actions, revocation, and disconnection without copying unnecessary creative content. Access and retention must be documented.

## Disconnection and Revocation

Disconnection must:

- stop new synchronization, polling, callbacks, and outbound actions;
- revoke the provider grant where supported;
- disable and securely dispose of local credentials according to policy;
- invalidate pending work that no longer has authority;
- preserve local authoritative records, content states, provenance, and revision history;
- preserve external mappings as inactive records when needed to explain origin or avoid accidental remapping;
- explain any remote copies that remain and any provider-side deletion the application cannot guarantee;
- allow safe reconnection without silently replaying old operations; and
- leave authoring, search, export, backup, and restoration fully usable.

Permission revocation or token expiration detected externally has the same fail-closed effect. Reauthorization must not automatically request broader scope or resume destructive operations without review.

## Provider Outage Behavior

Provider outage, latency, throttling, API change, account suspension, expired credentials, or network loss must not prevent ordinary local authoring, navigation, search, export, backup, or restoration.

The affected integration should:

- report a clear bounded status;
- preserve queued and reconciliation state safely;
- avoid blocking unrelated providers or local jobs;
- stop unsafe automatic retries;
- preserve local authoritative content unchanged;
- distinguish delayed, failed, and outcome-unknown external actions; and
- allow the owner to disconnect or continue local work.

The interface must not present stale external state as current without indicating its last verified time.

## Export and Portability

Strange Novelty exports must remain useful without any provider. Where relevant, documented exports should preserve:

- local stable identifiers and authoritative content;
- content states, Creative Contexts, and external provenance;
- external mappings in a safe, non-secret form when useful for migration or explanation;
- synchronization status and unresolved conflicts when omission would mislead; and
- referenced local private objects required for portability.

Exports must not include live credentials, tokens, authorization codes, webhook secrets, provider session data, or unrelated operational logs. Provider-specific identifiers may accompany provenance but never replace local identity.

An integration-specific export may help move to another provider, but no proprietary provider format may be the only exit path. Remote copies do not substitute for Strange Novelty export.

## Backup and Restoration Behavior

Backups must contain enough protected local integration state to explain and recover the archive, including required mappings, provenance, operation status, conflicts, and staged content within the documented retention scope.

Backups must not contain live provider credentials or secrets by default. If a future recovery design includes protected credential material, it requires an explicit security decision, separate key handling, and post-restore validation.

Restoration must:

- validate integration records, external mappings, versions, and references through ordinary migration rules;
- restore mappings as inactive or disconnected unless a separately approved procedure safely reestablishes authority;
- never resume polling, callbacks, synchronization, deletion, publishing, or outbound writes automatically;
- never treat restored tokens, callbacks, cursors, or queued jobs as current authority;
- reconcile external state only after explicit reauthorization and review;
- preserve provenance, content state, local identity, and unresolved conflicts; and
- remain successful even when every provider is unavailable.

A provider is not a backup destination merely because it holds a synchronized or exported copy.

## Security Requirements

- Authentication and authorization are enforced server-side for every integration operation.
- Each adapter and job receives only bounded Workspace, resource, operation, and credential authority.
- Providers never receive unrestricted Workspace, database, filesystem, object-storage, search, export, backup, AI, integration, or administrative access.
- Credentials and tokens remain server-side, protected at rest and in transit, excluded from Git, and redacted from logs and errors.
- Authorization flows resist request forgery, state confusion, account mix-up, replay, token substitution, and open redirects.
- Webhooks and callbacks require authentication, replay protection, validation, size limits, and bounded asynchronous processing.
- Provider URLs, redirects, downloads, and resource references must not create server-side request forgery, path traversal, injection, or unsafe file-processing paths.
- All inbound content is untrusted and follows upload, import, HTML, Markdown, document, archive, and rendering protections.
- Outbound requests use authenticated transport, verified endpoints, timeouts, response limits, and provider-specific allowlists.
- Destructive, sharing, publishing, permission, and administrative actions require explicit authority and risk-appropriate confirmation.
- Security failure fails closed and leaves authoritative content unchanged.
- An integration can be disabled independently during an incident.

## Testing Expectations

Before any future integration is accepted, testing should cover:

- core application operation with the integration absent, disconnected, revoked, expired, and unavailable;
- connection consent, account binding, permission display, denial, cancellation, reauthorization, and scope expansion;
- proof that requested provider permissions are the documented minimum;
- altered Workspace, integration, mapping, external identifier, resource, and operation attempts;
- credential isolation and absence from browser assets, Git, logs, errors, exports, backups, and provenance;
- inbound and outbound data minimization against the approved contract;
- import staging, validation, external provenance, Imported content state, review, and rejection;
- content-state and Canon protections for every inbound and synchronized path;
- source-of-truth, direction, base-version, and deletion semantics;
- local and remote concurrent edits, ambiguous identity, remote deletion, and explicit conflict resolution;
- idempotency under duplicate job execution, callback replay, timeout, restart, and outcome-unknown responses;
- bounded retry, backoff, quota exhaustion, pagination, cursor invalidation, and rate-limit handling;
- partial batches, resumability, compensation, and accurate status reporting;
- webhook authentication, replay, schema, size, ordering, duplication, unknown event, and account-mismatch cases;
- malicious provider content, identifiers, filenames, URLs, redirects, HTML, Markdown, documents, archives, and error payloads;
- provider outage without loss of local authoring, search, export, backup, or restoration;
- disconnection, provider-side revocation, remote-copy disclosure, and safe reconnection;
- export without secrets and with sufficient identity and provenance;
- restoration with all integrations inactive and all providers unavailable; and
- routine logging and telemetry exclusion of sensitive bodies and secret values.

Tests should use synthetic content and provider fixtures or controlled test accounts. Destructive and publishing actions require sandboxed verification and must never target real private content during routine testing.

## Integration Invariants

- Version 1 is fully usable without any external integration.
- No external integration is required for the core authoring workflow.
- The authoritative archive remains inside Strange Novelty.
- No integration is the sole custodian of manuscripts, artwork, metadata, provenance, exports, or backups.
- Every integration requires explicit author authorization for a documented purpose.
- Permissions are least-privilege and bounded by resource, operation, data, duration, and identity.
- Read, write, delete, publish, share, and administrative permissions remain distinct.
- Broad account-wide access is never requested merely for implementation convenience.
- Credentials and tokens remain server-side and are never committed to Git or exposed to the browser except through an approved provider-controlled authorization flow.
- Every integration is mediated by a dedicated adapter behind the application server.
- Providers receive no unrestricted Workspace, database, filesystem, object-storage, search, export, backup, AI, integration, or administrative access.
- Data-flow direction and source-of-truth rules are explicit for every workflow.
- Imported or synchronized data retains external provenance.
- External content never becomes Canon automatically.
- Provider identifiers never replace the primary identity of Strange Novelty records.
- Synchronization defines direction, source of truth, conflict, deletion, retry, and partial-failure behavior before implementation.
- Imported and synchronized material follows normal validation, state, provenance, ownership, concurrency, and review rules.
- External deletion never silently purges authoritative Strange Novelty content.
- Automatic last-write-wins is prohibited.
- Webhooks and callbacks are authenticated, replay-protected, validated, bounded, and unable to directly authorize state changes.
- Provider failure never prevents ordinary local authoring, search, export, backup, or restoration.
- Disconnecting leaves the core archive usable and does not erase provenance.
- Restoration never silently reactivates integrations, credentials, callbacks, queued work, or synchronization.
- Sensitive creative content and integration secrets never appear in routine logs, analytics, errors, traces, or telemetry.
- Integration failure fails closed where content, authority, privacy, or external side effects are at risk.

## Explicit Non-Decisions

This document does not decide:

- which, if any, external integration is implemented after Version 1;
- any document, storage, email, publishing, media, research, automation, or other provider;
- an authorization protocol, callback protocol, synchronization protocol, SDK, API style, or transport library;
- an application framework, integration framework, job system, scheduler, or implementation language;
- token format, credential storage product, secret manager, or encryption product;
- provider permission names, account model, resource hierarchy, or authorization-screen design;
- whether a future workflow uses import, export, one-way synchronization, bidirectional synchronization, or action-only behavior;
- external mapping schema, cursor representation, or idempotency mechanism;
- polling schedules, callback endpoints, retry parameters, rate limits, quotas, or batch sizes;
- automatic merge algorithms or a conflict-resolution interface;
- provider-specific file formats, document models, mail models, publishing models, or metadata mappings;
- integration staging and credential retention periods;
- whether protected credentials ever belong in a separately designed disaster-recovery mechanism;
- logging, monitoring, alerting, auditing, or incident-management products; or
- any change to Version 1 product scope.

Provider-specific choices require a demonstrated workflow, approved scope change, security and privacy review, data-flow and permission analysis, acceptance criteria, recovery design, and appropriate architecture decision records before implementation depends on them.

## Open Questions

1. Which demonstrated workflow should justify the first post-Version 1 integration?
2. What minimum local capabilities and roadmap entry criteria must be complete before integration work begins?
3. Is the first workflow inbound import, outbound copy, one-way synchronization, bidirectional synchronization, or an action-only operation?
4. What exact records, fields, objects, metadata, and provider resources does that workflow require?
5. What is authoritative on each side for every mapped field or artifact?
6. Which provider permissions are strictly necessary, and are they narrow enough to accept?
7. How will the owner understand consent, data direction, remote effects, retention, and disconnection consequences?
8. What external account, resource, and identity mix-up threats must the authorization flow prevent?
9. How will credentials be protected, rotated, revoked, and recovered without entering Git, exports, or routine backups?
10. What local and external versions or change markers define the synchronization base?
11. What constitutes a conflict, and which cases always require author review?
12. What are the explicit local and remote deletion semantics?
13. Which external operations require idempotency, reconciliation, or protection from duplicate side effects?
14. How are outcome-unknown requests resolved when the provider lacks an idempotency mechanism?
15. What atomic unit, batch behavior, and compensation rules apply to partial failure?
16. What polling, callback, pagination, rate, quota, size, concurrency, and retention limits are appropriate?
17. How will callbacks be authenticated and replay-protected for the selected provider without trusting their payload as authority?
18. What provider URL-fetching or file-processing behavior introduces request-forgery, upload, archive, or parser risk?
19. Which external identifiers and mappings must exports and backups preserve?
20. What integration records are restored inactive, and what explicit procedure permits safe reconnection?
21. What provider-side copies or retained data remain after disconnection, deletion, or account loss?
22. Which provider privacy, human-access, subprocessor, geographic, incident, deletion, and retention terms are acceptable?
23. What operational and audit events are necessary without exposing transferred creative content?
24. What outage duration and stale-state behavior are acceptable while local work continues?
25. Which synthetic fixtures, test accounts, failure simulations, and destructive-operation safeguards are required?
26. Which choices require architecture decision records before a future integration enters implementation scope?
