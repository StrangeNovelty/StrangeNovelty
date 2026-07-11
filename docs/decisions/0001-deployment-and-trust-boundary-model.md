# ADR-0001: Deployment and Trust-Boundary Model

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the deployment and authority model but does not itself select technologies or providers.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; security, privacy, data, AI-context, operations, and recovery perspectives

## Context

Strange Novelty is intended to be a private, secure, authenticated web workspace for one author and artist. It will hold unpublished manuscripts, notes, structured story knowledge, provenance, AI suggestions, private objects, exports, and backups. A single human owner reduces collaboration complexity but does not reduce the value of the protected material or eliminate risks from account takeover, browser compromise, malicious input, provider exposure, operational error, or data loss.

The architecture documents already identify logical components and invariants, but implementation needs a durable decision about where authority resides before selecting frameworks, runtimes, databases, authentication mechanisms, hosting, storage, AI services, or observability products. Without that decision, a convenient early implementation could place credentials, database access, validation, or durable writes in the browser and silently establish a trust model that conflicts with the product’s private-by-default promise.

The old Story Engine provides relevant contrary evidence. It is a local desktop/webview application whose frontend loads the local database directly, performs database writes, stores an external-service credential in the application database, and calls the AI provider from client code. Its webview has direct SQL permissions and several filesystem-oriented native commands. That design may have supported a personal single-machine workflow, but it does not satisfy Strange Novelty’s authenticated private-web boundary, server-side authorization, provider isolation, secret handling, or bounded recovery requirements. See `docs/reference/story-engine-audit.md`.

This ADR therefore decides the deployment and authority model at a conceptual level. It deliberately leaves technology and vendor choices to later ADRs.

The decision must preserve these established requirements:

- only the authenticated owner may access Version 1 creative content;
- every private operation is authorized against the current owner and Workspace;
- client-side hiding is not authorization;
- content states and contextual Canon change only through validated, explicit author actions;
- AI receives only bounded, deliberately selected context through an isolated gateway;
- external providers never receive unrestricted Workspace access;
- exports and backups remain private;
- restoration cannot bypass validation, provenance, migration, or authority rules; and
- the application remains small enough to implement, operate, test, and recover as one cohesive Version 1 system.

## Decision

If accepted, Strange Novelty will use a **cohesive private web application with server-enforced trust boundaries**.

The deployment and authority model is:

1. Strange Novelty is a private authenticated web application for one owner in Version 1.
2. The browser is an untrusted presentation client. It presents data, collects intent, and maintains limited interface state, but it is not an authority for identity, ownership, validation, state transitions, or durable writes.
3. The application server is the primary policy-enforcement boundary. It authenticates requests, validates sessions, authorizes operations, validates input, applies domain rules, mediates persistence, and coordinates bounded external work.
4. Authentication, authorization, Workspace ownership, validation, content-state transitions, provenance changes, concurrency checks, and durable writes are enforced server-side.
5. Every private read and write is authorized against the current authenticated owner and the authoritative Workspace association of the affected records.
6. The browser never receives database credentials, provider secrets, backup credentials, encryption material, administrative credentials, or unrestricted storage authority.
7. The browser never connects directly to the primary database and never calls the AI provider directly.
8. Background jobs act as separate, narrowly authorized principals. They receive a bounded task and must revalidate affected records, current versions, Workspace ownership, and applicable rules before committing results.
9. Private object storage, if Version 1 needs it, is accessed through the server or through short-lived, single-purpose, narrowly scoped grants issued only after server authorization.
10. AI calls cross a distinct external trust boundary through the server-side AI gateway. The provider receives one approved request and no application credentials or system access.
11. Export, backup, migration, and restoration use separate bounded workflows with explicit authorization, job state, validation, and auditability. They do not share unrestricted browser or background authority.
12. Restoration occurs in an isolated or deliberately prepared target. Restored data is validated, migrated, and tested before it can become active.
13. Administrative access is exceptional, least-privileged, attributable, separately protected where appropriate, and auditable. It cannot silently bypass content protection, author approval, provenance, or restoration rules.
14. Logs, telemetry, traces, analytics, and error reporting minimize sensitive metadata and exclude routine manuscript bodies, AI prompt and response bodies, object contents, credentials, exports, and backup contents.
15. Version 1 may deploy as one cohesive application and may colocate logical components where the security and operational constraints remain enforceable. It does not require microservices.
16. Internal boundaries remain explicit among browser presentation, application services, persistence, private objects, background jobs, AI gateway, operational logging, export/backup, migration, and restoration, even when some run in the same deployment.
17. Version 1 does not include multi-user collaboration, public sharing, a general integration platform, or independently deployed services without demonstrated need.
18. Exact hosting, framework, runtime, language, database, object storage, authentication, AI, job, logging, monitoring, and deployment products remain undecided.

This ADR defines authority, not topology count. “Application server” means the trusted server-side execution boundary responsible for policy enforcement. “One cohesive application” permits internal modules and separately executed bounded jobs without requiring each logical component to be an independent network service.

## Trust Boundaries

### Browser and network boundary

The browser, browser extensions, client device, network, URLs, cookies presented by the client, local state, request bodies, uploaded files, and imported content are outside the trusted application boundary.

The browser may:

- display server-authorized data;
- submit author intent and concurrency tokens;
- request supported searches, AI tasks, exports, backups, or recovery actions;
- upload supported untrusted files through bounded workflows; and
- receive narrowly scoped private-object access when explicitly authorized.

The browser may not:

- assert ownership or permission as an authoritative fact;
- choose an unrestricted Workspace scope;
- construct trusted content-state or provenance events;
- hold server or provider secrets;
- issue database queries;
- write directly to authoritative storage;
- select hidden AI context outside the server-validated manifest; or
- activate restored data.

Protected transport is required, but transport security does not make the browser trusted.

### Application-service boundary

The application server is the central trusted policy boundary. It is responsible for:

- authenticating the owner and validating the current session;
- authorizing every private operation;
- scoping queries by Workspace;
- validating untrusted input and supported operation types;
- enforcing hierarchy, stable identity, Links, provenance, lifecycle, and content-state rules;
- enforcing contextual Canon and explicit author approval;
- enforcing revision and stale-write rules;
- issuing bounded work to jobs and the AI gateway;
- mediating private storage access; and
- producing privacy-conscious audit and operational events.

Server trust is not unlimited. Server components receive only the credentials and data necessary for their responsibilities, and high-risk operational paths remain separated where practical.

### Persistence boundary

The primary database and any private object storage are private infrastructure. They are not reachable directly from the browser. Network and credential access is limited to approved application, migration, backup, and restoration paths.

The primary database is authoritative for structured Workspace state. Private object storage is subordinate to authoritative metadata and must not become an undocumented secondary archive. Search indexes, backlinks when materialized, caches, and other derived data remain rebuildable.

### Background-job boundary

The background-job system is logically distinct from interactive requests. A job carries only:

- a stable job and originating-operation identifier;
- one Workspace;
- one bounded task type;
- required record or artifact references;
- the minimum service authority needed;
- relevant base versions or consistency markers; and
- retry and expiration constraints.

Job payloads do not contain owner credentials, provider secrets that are unnecessary to the worker, entire Workspace dumps, or implicit approval for authority-changing actions.

### AI-provider boundary

The AI provider is external and untrusted with respect to application authority. Only the AI gateway may transmit a validated, previewed, task-specific context manifest. The provider receives no database, filesystem, object-storage, search, export, backup, integration, job, or administrative access.

Provider output is untrusted input. Every retained result begins as AI suggestion and cannot modify source content or become Canon automatically.

### Operational boundary

Administrative tools, deployment systems, secret delivery, logs, telemetry, error reporting, and support workflows are distinct operational security domains. Access to operate the application is not routine permission to read manuscripts.

Operational systems receive minimum necessary metadata. Sensitive content access for an exceptional incident must be deliberate, attributable, and bounded.

### Export, backup, migration, and restoration boundary

Exports and backups remain private after leaving the live application. Migration and restoration ingest untrusted artifacts into an isolated path before activation. These workflows use separate authorization, integrity, format, provenance, migration, and audit checks rather than ordinary CRUD authority.

## Authority by Component

| Component | Permitted authority | Prohibited authority |
| --- | --- | --- |
| Browser client | Present authorized data; submit intent; hold limited UI state; receive bounded responses | Database access; provider secrets; owner or Workspace self-assertion; unrestricted storage; authoritative state transitions |
| Application server | Authenticate, authorize, validate, apply domain rules, coordinate persistence and bounded work | Silent author approval; indiscriminate data exposure; bypass of provenance or content-state invariants |
| Primary database | Persist authoritative structured state under server-mediated access | Public or browser access; policy decisions based only on caller-supplied fields |
| Private object storage | Store protected objects referenced by authoritative metadata | Public-by-default objects; unrestricted browser credentials; sole undocumented archive |
| Background job | Execute one bounded task using scoped service authority | Reuse owner session; expand task scope; promote Canon; overwrite stale records; grant itself new permissions |
| AI gateway | Construct and submit approved task-specific requests; normalize responses; attach provenance | Provider access to application systems; unrestricted retrieval; autonomous source changes |
| AI provider | Process one bounded request and return untrusted output | Workspace browsing; tool or credential access; Canon or application authority |
| Export subsystem | Read an authorized consistent scope and produce a validated private artifact | Include secrets or unrelated logs; publish or expose artifacts publicly |
| Backup subsystem | Capture required recoverable state and integrity metadata | Treat existence as verification; include live sessions or credentials without an approved recovery design |
| Migration process | Apply deterministic, reviewed representation changes in a bounded procedure | Silently change creative meaning, identity, state, or provenance |
| Restoration process | Validate and reconstruct in isolation; propose activation after tests | Overwrite live data through ordinary requests; activate credentials, jobs, or integrations silently |
| Administrator/operator | Perform documented exceptional operational tasks with least privilege | Routine manuscript access; silent content edits; bypass of author approval, validation, or audit |

## Request and Write Flow

### Private read

1. The browser submits a request over protected transport.
2. The application server validates the current authenticated session.
3. The server identifies the owner and authorized Workspace from trusted server-side state.
4. The server authorizes the requested operation and record type.
5. The server scopes persistence access to the Workspace and validates record ownership.
6. The server returns only data needed for the authorized view.
7. The browser renders the result as untrusted presentation data using the required client-side security controls.

Record identifiers, URLs, hidden controls, cached pages, and client-supplied Workspace fields never replace server authorization.

### Durable write

1. The browser submits an explicit action, target identifiers, proposed values, and required base versions.
2. The server validates the session, reauthorizes the operation, and validates Workspace ownership.
3. The server validates input shape, size, supported fields, content safety, lifecycle status, and relationship references.
4. The server loads current authoritative state and checks concurrency.
5. The server applies domain rules, including content-state, contextual Canon, provenance, hierarchy, Link, revision, and author-approval rules.
6. The server performs the durable write within the selected consistency boundary.
7. The server records required revision, provenance, audit, and job events without placing manuscript bodies in routine logs.
8. The server returns the resulting version and bounded response.

Stale, unauthorized, malformed, or ambiguous writes fail closed. Automatic last-write-wins is prohibited.

## Background-Job Flow

1. An authenticated, authorized server action creates a bounded job record.
2. The job record identifies its Workspace, task type, source references, base versions, requested output, authority scope, and retry policy.
3. A worker claims the job using service identity, not the owner’s browser session.
4. The worker retrieves only required inputs through controlled interfaces.
5. Before any commit, the worker revalidates Workspace ownership, current record versions, source availability, authorization-relevant state, and applicable domain rules.
6. If sources changed, authority expired, or the operation became invalid, the worker records a conflict or bounded failure instead of overwriting current state.
7. The worker commits only its permitted result, records status and provenance, and releases transient authority.
8. The browser obtains status through the application server.

Retries must be idempotent or safely reconciled. Jobs cannot infer approval to promote Canon, accept imported content, publish, purge, restore, or repeat externally visible actions.

## AI Request Flow

1. The owner explicitly invokes the supported scene-focused review capability.
2. The application server assembles candidate context under the AI context architecture.
3. The browser displays the task and context preview without receiving provider credentials.
4. The owner submits the exact task and manifest.
5. The server validates the current authenticated session, reauthorizes the operation, and revalidates every source. Recent authentication may be required only when justified by the security policy.
6. The server-side AI gateway constructs a bounded provider request from the approved manifest.
7. The gateway obtains the provider credential through server-side secret handling and sends the request over protected transport.
8. The provider returns untrusted output to the gateway.
9. The gateway validates size and shape, normalizes the output, and attaches bounded provenance.
10. The server displays or stores the result as AI suggestion.
11. Any later author action on the suggestion follows ordinary validation, concurrency, provenance, and state-transition rules.

The provider never sees an application credential or receives a callable route into database, storage, search, export, backup, integrations, or administration. Failure leaves source content unchanged.

## Export and Backup Flow

### Export

1. The authenticated owner explicitly selects an export scope.
2. The application server authorizes the scope and records the operation.
3. A bounded export process reads a consistent, Workspace-scoped representation and required private objects.
4. It produces a versioned artifact and manifest in protected storage.
5. Validation confirms expected structure before completion is reported.
6. The server provides private, short-lived, authorized access to the artifact.

Exports exclude credentials, sessions, encryption keys, provider tokens, and unrelated operational data.

### Backup

1. An authorized owner action or approved server-side schedule creates a backup job.
2. The job captures the complete required database state, private objects, format and migration metadata, manifest, and integrity evidence within a documented consistency boundary.
3. Verification checks expected components, references, object presence, and integrity.
4. A verified artifact is stored in a protected location sufficiently separated from live failure domains.
5. Backup status distinguishes creation, structural verification, and successful restoration testing.

The browser may request and observe these workflows but does not receive backup infrastructure credentials or unrestricted artifact storage access.

## Restoration Flow

1. The owner or separately authorized recovery operator initiates a protected restoration procedure.
2. The system establishes an isolated or deliberately prepared restoration target.
3. The restoration process authenticates and authorizes the operator independently of any credentials contained in the artifact.
4. It validates artifact format, version, integrity, expected record groups, private objects, references, and incomplete-operation markers.
5. It applies supported deterministic migrations while preserving stable identity, content states, Creative Context, provenance, revisions, and audit history.
6. It rebuilds or verifies derived indexes and backlinks.
7. It prevents restored sessions, credentials, tokens, integrations, callbacks, queued jobs, and provider access from becoming active automatically.
8. Representative authenticated checks verify hierarchy, content, revisions, Links, states, contexts, provenance, lifecycle behavior, and private objects.
9. Validation and test results are reviewed through an explicit activation decision.
10. Only after successful review does the restored target become active through a documented cutover or replacement procedure.

Failure leaves the existing authoritative archive intact or follows a tested rollback path. An ordinary browser request cannot replace the live database with an uploaded artifact.

## Administrative-Access Model

Administrative access is exceptional operational authority, not a second author role.

It must be:

- limited to documented deployment, security, backup, restoration, migration, and incident tasks;
- authenticated separately where the deployment and risk justify it;
- protected with strong factors appropriate to the access path;
- least-privileged by component, environment, operation, and duration;
- attributable to an individual or bounded service principal where supported;
- disabled, time-bounded, or just-in-time where practical;
- logged through privacy-conscious security events;
- unable to silently edit content, approve content-state changes, or impersonate authorial intent;
- unable to make restored or imported content Canon; and
- reviewed after emergency or break-glass use.

Operators do not routinely inspect manuscript content. Exceptional content access during recovery or incident response must have a documented purpose, minimum scope, and audit trail. Development and testing use synthetic data rather than production manuscripts, exports, backups, or database copies.

## Failure Behavior

The architecture favors integrity and explicit failure over hidden availability shortcuts.

- Identity, session, authorization, Workspace, validation, or concurrency uncertainty fails closed.
- A browser or client-side failure cannot commit a durable write without server acceptance.
- A partial request does not appear successful.
- A job that loses authority or observes changed source versions stops or records a conflict.
- Provider outage disables only the affected AI capability; local authoring, search, export, backup, and restoration remain available according to their own dependencies.
- Object-storage failure reports missing or incomplete objects and does not create authoritative references to nonexistent results.
- Logging and telemetry failure must not trigger fallback logging of manuscript bodies or secrets.
- Export and backup artifacts are not marked complete or verified when validation fails.
- Restoration failure cannot activate partial data or silently overwrite the live archive.
- Migration failure reports bounded transformation status and uses the documented recovery point.
- Administrative-access failure does not fall back to shared, anonymous, or browser-held credentials.
- Outcome-unknown external actions are reconciled before unsafe retry.

Specific availability, recovery-time, recovery-point, retry, timeout, and circuit-breaking targets remain later decisions.

## Rationale

The cohesive private web model best satisfies the current documents because it establishes one understandable enforcement boundary without requiring premature distributed infrastructure.

It provides:

- a consistent place to authenticate and authorize every private operation;
- a server-side boundary for Workspace ownership, validation, content state, contextual Canon, provenance, and concurrency;
- isolation of database, storage, backup, and provider credentials from the browser;
- a controlled route for bounded AI context and untrusted provider output;
- narrow service authority for jobs, exports, backups, migrations, and restoration;
- a deployment that can remain operationally small for one owner;
- a clear path to separate components later if security, workload, failure isolation, or maintainability evidence requires it; and
- independence from any particular framework, database, hosting product, or external provider.

This decision also directly addresses lessons from the old Story Engine without assuming its local desktop implementation should be preserved.

## Alternatives Considered

### Alternative: local desktop application with direct local database access

This approach can minimize hosting and network exposure, support offline work, and make local persistence straightforward. The old Story Engine demonstrates its practical appeal for a solo user.

It is not selected because Strange Novelty’s current product scope explicitly defines a private authenticated web application. Direct webview access to local data also concentrates trust in client code, complicates server-side authorization and secret isolation, couples deployment to a device, and does not naturally satisfy the chosen browser/server, AI-gateway, job, administrative, and recovery boundaries.

A future offline or desktop client could be reconsidered as a separate capability, but it must not silently replace this deployment and authority model.

### Alternative: browser client with direct backend-service or database access

This approach can reduce custom server code by letting the browser use hosted database, object-storage, authentication, or provider SDKs directly. Fine-grained backend policies may offer useful defense in depth.

It is not selected as the authority model because browser-held service access increases credential and policy exposure, spreads authorization across client and provider configuration, risks direct object enumeration, and makes consistent domain enforcement harder. Client-side or provider-side rules may supplement the server but cannot replace the application-server boundary. The browser must not connect directly to the primary database or AI provider.

### Alternative: early microservices decomposition

This approach can isolate workloads and allow independent scaling or technology selection for authentication, content, AI, search, jobs, export, and recovery.

It is not selected for Version 1 because the product serves one owner, has a narrow initial workflow, and prioritizes low maintenance and recoverability. Early service distribution would add network trust, credentials, deployment coordination, observability, consistency, backup, and incident-response complexity before workload evidence justifies it.

Logical boundaries are preserved so later separation remains possible.

### Alternative: cohesive private web application with server-enforced boundaries

This is the proposed decision. It centralizes policy enforcement while keeping internal modules explicit. It supports a small initial deployment without treating colocated components as one unrestricted trust domain.

Its principal costs are operating a private server-side deployment, building explicit authentication and recovery, and maintaining server-mediated persistence and external-service calls. Those costs follow directly from the private authenticated web product promise and are preferable to distributing authority into the browser.

## Evidence

### Product and architecture evidence

- `README.md` describes a private, secure web-based creative workspace and excludes private material from source control.
- `docs/product/vision.md` and `docs/product/principles.md` make privacy, authorial control, provenance, portability, backup, and recovery core product properties.
- `docs/product/scope.md` requires authenticated private desktop-class browser access and denies public sharing for Version 1.
- `docs/product/roadmap.md` requires secure single-user authentication, tested restoration, and documented trust boundaries before implementation.
- `docs/architecture/overview.md` defines the browser as untrusted, the application server as the policy boundary, and external services as subordinate.
- `docs/architecture/data-model.md` requires explicit Workspace ownership, stable identity, concurrency checks, content states, provenance, migration, and restoration.
- `docs/architecture/security.md` requires server-side authorization, secret isolation, private storage, bounded jobs, protected backups, and isolated restoration.
- `docs/architecture/ai-context.md` requires explicit invocation, server validation, bounded manifests, provider isolation, and AI-suggestion state.
- `docs/architecture/integrations.md` requires adapters, least privilege, local authority, disconnection, and provider-independent recovery for future integrations.

### Reference-system evidence

The static old Story Engine audit found:

- direct frontend SQLite access;
- broad webview SQL permission;
- client-side provider calls and credential use;
- no application authentication, session, authorization, or Workspace boundary;
- direct filesystem-oriented native commands;
- hard deletion, incomplete provenance, and no contextual Canon model; and
- raw database-copy backups without demonstrated integrity verification or tested restoration.

These observations support defining the authority boundary before choosing the new stack. They do not prove that a particular new technology is correct.

### Evidence still required

Before this ADR moves from Proposed to Accepted, review should confirm:

- that the owner accepts operating or relying on a server-side private web deployment;
- the acceptable network exposure and access pattern;
- whether any offline requirement materially changes the model;
- that the initial recovery process is operable for one owner; and
- that later technology candidates can satisfy these boundaries without unreasonable complexity.

## Consequences

### Positive

- One primary policy boundary governs private reads and writes.
- Secrets, database access, and provider access remain outside browser code.
- Workspace ownership and domain invariants can be tested consistently.
- Background jobs and recovery operations receive narrow, explicit authority.
- AI context and output pass through a controlled server-side boundary.
- The deployment can remain cohesive and low-complexity initially.
- Future component separation remains possible without changing the authority model.
- Exports, backups, and restoration are designed as protected workflows rather than filesystem shortcuts.
- The architecture remains provider- and framework-neutral.

### Negative

- Version 1 requires a server-side runtime and operational deployment even for one owner.
- Authentication, session handling, secret management, backups, monitoring, and administrative recovery must be operated securely.
- Offline-first authoring is not provided by this decision.
- Server mediation adds implementation work and may add latency compared with direct local database access.
- Private object downloads and uploads require scoped access mechanisms or server proxying.
- Local development must preserve server-side boundaries rather than bypass them for convenience.

### Neutral or Operational

- A cohesive deployment may still use separate processes for jobs or recovery when needed.
- Logical modules do not imply independently deployed services.
- Managed services may later be selected, but they remain behind the server boundary.
- Authentication may be delegated later, but application authorization and Workspace checks remain server-side.
- Database constraints, storage policies, and infrastructure controls may reinforce authorization as defense in depth.
- The deployment location and provider remain open.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Application-server compromise | Broad access to private content and service credentials | Least privilege, component-specific secrets, patching, secure deployment, monitoring, bounded administrative access, tested recovery | A trusted runtime must access necessary plaintext and can remain a high-value target |
| Single cohesive deployment creates a failure domain | Local authoring and server operations may be unavailable together | Verified backups, separate recovery copies, documented restore, process isolation where justified | Availability remains lower than a mature distributed system |
| Internet-exposed sign-in is attacked | Account takeover or denial of service | Strong authentication, MFA evaluation, throttling, secure sessions, alerts, restricted network exposure where appropriate | Credential phishing and endpoint abuse cannot be eliminated |
| Server becomes an oversized module | Maintainability and policy inconsistency | Explicit internal modules, typed interfaces, deny-by-default routes, architecture tests, later extraction based on evidence | Cohesive deployment still requires disciplined boundaries |
| Background job uses stale authority or data | Incorrect overwrite or unauthorized effect | Scoped job identity, base versions, revalidation before commit, idempotency, conflict status | Long-running work can still require complex reconciliation |
| Short-lived object grants leak | Temporary unauthorized object access | Narrow object/operation scope, short expiry, protected transport, no public defaults, audit and cache controls | A valid grant can be used until it expires |
| Administrative access bypasses author controls | Silent content exposure or mutation | Separate authentication, least privilege, time bounds, audit, no routine content access, break-glass review | Infrastructure operators may retain technical capability depending on provider choice |
| Privacy leakage through operations | Manuscript or metadata reaches logs or vendors | Structured allowlists, redaction by construction, no request bodies, provider review, retention limits | Coarse metadata can still reveal usage patterns |
| Restoration activates malicious or stale state | Corruption, credential reuse, or authority changes | Isolation, integrity and compatibility checks, inactive credentials/jobs/integrations, representative tests, explicit activation | A trusted but semantically flawed backup may pass structural checks |
| Provider-specific service pressures architecture | Lock-in or weakened boundary | Provider adapters/gateways, internal identities, documented exports, later ADRs, exit testing | Some provider constraints may still affect operations |
| Server-mediated model weakens offline use | Author cannot work during network/server outage | Reliability targets, local recovery documentation, possible future bounded offline design | Version 1 may require connectivity to the private endpoint |

## Security and Privacy Review

- Security-sensitive: Yes
- Primary reference: `docs/architecture/security.md`
- Additional references: `docs/architecture/ai-context.md`, `docs/architecture/integrations.md`, and `docs/architecture/data-model.md`

### Protected assets

The decision affects manuscripts, notes, structured records, revisions, content states, contextual Canon, provenance, private objects, search data, AI inputs and outputs, credentials, sessions, exports, backups, audit records, and availability.

### Affected trust boundaries

It establishes browser/network, application-service, persistence, private-object, job, AI-provider, operational, export/backup, migration, and restoration boundaries.

### Privacy implications

The server necessarily processes private content for authorized requests. Data exposure is minimized by returning view-specific data, issuing task-specific job authority, sending bounded AI context, excluding manuscript bodies from routine telemetry, and keeping providers outside the archive boundary.

The eventual hosting and administrative model will determine which infrastructure operators can technically access stored or in-process content. That residual privacy question must be evaluated in later provider and encryption ADRs.

### Credential and permission implications

Browser-held database, AI-provider, backup, and unrestricted object-storage credentials are prohibited. Application, job, migration, backup, restoration, and administrative principals require separate least-privilege scopes where practical. Authentication identity does not by itself grant storage or administrative access.

### Required security testing

Later implementation must test:

- unauthenticated and cross-Workspace denial for every private operation;
- altered identifiers and client-supplied ownership fields;
- session expiration, revocation, and state-changing request protection;
- absence of server, database, storage, provider, and backup credentials from browser assets;
- direct database and provider network inaccessibility from the browser;
- job scope, revalidation, stale-source, idempotency, and retry behavior;
- private object grant scope, expiration, cache behavior, and public-access denial;
- AI manifest authorization and provider isolation;
- export and backup artifact authorization and secret exclusion;
- isolated restoration, inactive restored credentials, integrity failure, and explicit activation;
- administrative access authentication, audit, and inability to silently create author approval; and
- log, telemetry, trace, analytics, and error-report content boundaries.

### Applicable security invariants

This decision preserves the security architecture’s requirements that Strange Novelty is private by default, only the authenticated owner accesses creative content, authorization is server-side, secrets remain out of the browser and Git, providers receive no unrestricted access, private objects are not public, backups remain private, and restoration does not bypass normal rules.

### Residual risk

The application server is a high-value trusted component. At-rest encryption cannot protect content from a compromised server while it processes authorized requests. Administrative and hosting-provider access cannot be fully evaluated until the deployment and provider choices are proposed. Those risks remain explicit follow-up items rather than reasons to move authority into the browser.

## Product and Architecture Alignment

### Product vision and principles

The decision supports:

- private-by-default operation;
- one authorized author and artist;
- authorial control over creative authority;
- deliberate AI context;
- transparent and reversible actions;
- dependable writing and navigation;
- exportability, backup, restoration, and provider exit; and
- a narrow, maintainable Version 1.

### Scope and roadmap

The decision implements no feature and selects no technology. It establishes the documented trust boundary needed by Phase 0 before Phase 1 application code. It preserves Version 1 exclusions for public sharing, teams, real-time collaboration, native mobile applications, general integrations, and broad AI behavior.

### Architecture

The decision makes durable the architecture overview’s application-server enforcement model. It preserves:

- explicit Workspace ownership and stable identity;
- server-side content-state, contextual Canon, provenance, lifecycle, and concurrency rules;
- bounded AI invocation and AI-suggestion state;
- future adapter-mediated integrations;
- private storage and privacy-conscious operations; and
- protected export, backup, migration, and isolated restoration.

### Required normative-document updates

None are required for this Proposed draft. It is consistent with the current product and architecture documents. If review changes the authority model, affected documents must be updated before acceptance.

### Invariants preserved

No client, job, provider, integration, operator, migration, or restoration artifact can silently acquire authorial authority. No external service becomes the sole custodian of the archive. The old Story Engine remains read-only reference material.

## Migration, Portability, and Recovery

This decision does not authorize migration from the old Story Engine. It establishes that any future import or migration runs through a bounded server-side workflow, not through direct browser database access.

Legacy material must:

- enter through an explicit Import Batch;
- be treated as untrusted input;
- retain old identifiers only as external provenance;
- receive Strange Novelty stable identity and Workspace ownership;
- begin as Imported content unless a more conservative staging state applies;
- preserve unresolved mappings and partial failures;
- avoid automatic Canon promotion; and
- pass ordinary validation, concurrency, review, export, backup, and restoration rules.

Portability is preserved by keeping provider identifiers and credentials outside core record identity, maintaining documented exports, and requiring backups that can restore without AI or future integrations.

Recovery is preserved by separating live operation from backup and restoration authority. Backups require protected copies outside the immediate live failure domain. Restoration must succeed without external AI or integrations and must validate a representative Workspace before activation.

Future technology ADRs must explain how their choices support export, backup, verified restoration, migration away, and recovery when the selected provider is unavailable.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Confirm the acceptable Version 1 network exposure and owner access pattern.
- [ ] Decide whether offline use is a requirement or explicitly deferred behavior.
- [ ] Define the initial application module boundaries within the cohesive deployment.
- [ ] Propose an ADR for application runtime, framework, and server rendering/client approach.
- [ ] Propose an ADR for primary database and physical persistence.
- [ ] Propose an ADR for authentication, session, authorization, and account recovery.
- [ ] Propose an ADR for secret and encryption-key management.
- [ ] Decide whether Version 1 requires private object storage beyond exports and backups.
- [ ] Propose an ADR for background-job execution and scoped service identity.
- [ ] Propose an ADR for the AI provider and server-side gateway implementation after provider terms are evaluated.
- [ ] Define operational logging, security events, monitoring, and administrative-access procedures.
- [ ] Define export format and validation.
- [ ] Define backup format, destination, consistency mechanism, integrity checks, schedule, and retention.
- [ ] Define isolated restoration, activation, rollback, and representative acceptance tests.
- [ ] Create architecture tests that enforce browser, server, persistence, job, AI, and recovery boundaries.
- [ ] Update the ADR index only when repository policy calls for indexing this actual record.

No follow-up item authorizes package installation, provider commitment, application code, migration, deployment, or secret creation until the relevant decision is accepted.

## Implementation References

- Not yet available.
- The repository remains documentation-only at the time of this proposal.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
