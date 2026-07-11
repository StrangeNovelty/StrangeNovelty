# Strange Novelty Architecture Overview

## Purpose

This document defines the conceptual architecture for Strange Novelty.

It describes the system’s major components, responsibilities, trust boundaries, data flows, deployment shape, reliability expectations, and architectural constraints. It intentionally does not select a final technology stack. Product-specific data structures, security controls, AI context rules, integration contracts, and durable technology choices belong in their respective architecture documents and decision records.

Strange Novelty is a private, secure, web-based creative workspace for one author and artist. Its architecture must protect unpublished creative material, preserve authorial authority and provenance, support recovery and portability, and keep AI and future integrations subordinate to the author-controlled workspace.

## Architectural Goals

The architecture should:

- provide a dependable private workspace for a solo creator;
- deny access to private content unless a request is authenticated and authorized;
- keep the application’s authoritative creative archive under the author’s control;
- preserve meaningful content states, contextual canon, provenance, links, and backlinks;
- support drafting and revision without losing narrative context or reasonable recovery paths;
- make important actions understandable, intentional, and reversible where practical;
- limit AI context to material deliberately selected for a specific task;
- prevent AI output, imported material, and external data from silently acquiring authority;
- support useful, documented exports that can be inspected outside the application;
- support complete backups that can be verified and restored;
- avoid dependence on an opaque format, one hosted service, or one external integration;
- keep Version 1 small enough to operate, understand, secure, test, and recover;
- leave room for later capabilities through stable boundaries rather than speculative abstractions.

## Architecture Constraints Inherited from the Product Principles

The following product principles constrain every later architecture and technology decision:

1. **The author is the final authority.** Automation may propose or assist, but it must not silently rewrite authoritative material, resolve creative conflicts, or promote content to canon.

2. **Content states remain distinct.** Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion must remain distinguishable in storage, application behavior, exports, backups, and restoration.

3. **Canon is contextual.** The architecture must not assume a single universal truth across every world, series, book, timeline, version, or other creative context.

4. **Event, reveal, and knowledge are separate concepts.** Future architecture must be able to represent story chronology, reader revelation, and character knowledge independently.

5. **Links and backlinks are foundational.** The system must preserve explicit relationships and support navigation in both directions without requiring every relationship to fit an unrestricted or overly complex graph model.

6. **AI scope is deliberate.** AI operations must use bounded, understandable context. Indiscriminate ingestion of a story directory or creative archive is prohibited.

7. **Privacy is the default.** Creative content, credentials, personal information, AI inputs and outputs, exports, backups, and operational data must be treated conservatively.

8. **Ownership includes an exit path.** The author must be able to export, back up, verify, restore, and migrate the creative archive.

9. **Imports do not imply authority.** Imported material must preserve its source and remain distinguishable from author-approved content until explicitly reviewed.

10. **Structure should guide without overconstraining.** The core narrative hierarchy provides a clear default while links allow material to cross structural boundaries.

11. **The system serves one creator.** Architecture should favor focus, trust, low maintenance, and straightforward operation over enterprise collaboration or organizational administration.

12. **Transparency and reversibility take precedence over clever automation.** Important operations must expose their inputs and effects sufficiently for the author to understand and review them.

13. **The first release remains narrow.** Future possibilities must not introduce unnecessary Version 1 complexity.

## System Context

Strange Novelty is a private web application used by one authorized author from a supported desktop or laptop browser.

Within the system boundary, the application stores and manages:

- worlds, series, books, chapters, and scenes;
- scene drafts and revisions;
- characters and locations;
- supported links and backlinks;
- content states and their creative contexts;
- basic provenance;
- authentication and session-related application records;
- AI request and suggestion records where retention is required;
- export, backup, verification, and restoration metadata.

The application may communicate with external systems only through explicit boundaries. In Version 1, the principal external system is an AI provider used for one narrowly defined, author-invoked capability. Future versions may add external document, storage, email, publishing, or other services through dedicated integration adapters.

External services are not part of the authoritative core of Strange Novelty. Loss or disconnection of an AI provider or future integration must not make the primary creative archive inaccessible.

## Major Components

### Browser Client

The browser client provides the author-facing workspace.

Its responsibilities include:

- presenting sign-in and sign-out workflows;
- navigating the narrative hierarchy, entities, links, and backlinks;
- supporting scene drafting and revision;
- displaying content states, provenance, and creative context;
- initiating intentional state changes and other authority-changing actions;
- presenting search results and item context;
- showing or clearly describing the context of supported AI operations;
- displaying AI results as reviewable suggestions;
- initiating exports, backups, or restoration-related workflows where appropriate;
- presenting failures without implying that an unsuccessful operation changed authoritative content.

The browser client is not a trusted custodian of application secrets or unrestricted storage credentials. It must not enforce security solely through hidden controls or client-side checks. Authorization and validation of authoritative changes belong at the application server boundary.

The client may retain limited local interface state when useful, but browser-local data must not become the sole copy of authoritative creative work.

### Application Server

The application server is the central enforcement and coordination boundary.

Its responsibilities include:

- authenticating requests and validating sessions;
- authorizing every operation involving private or administrative resources;
- applying domain rules for hierarchy, content states, provenance, links, and backlinks;
- validating and persisting authoritative changes;
- coordinating revision and recovery behavior;
- performing or coordinating search;
- issuing narrowly scoped work to the background job runner;
- assembling or coordinating bounded AI requests through the AI gateway;
- coordinating exports, backups, verification, and restoration;
- mediating access to private object storage;
- invoking future integration adapters;
- producing privacy-conscious operational events.

The application server must remain the authoritative policy enforcement point even when work is executed asynchronously. Background jobs, AI calls, and integrations must not bypass its domain and authorization rules.

### Primary Database

The primary database stores the authoritative structured state of the workspace.

It is expected to contain, directly or by durable reference:

- narrative hierarchy records;
- scene content and revision information appropriate to the selected revision model;
- characters and locations;
- links and the information necessary to derive or retrieve backlinks;
- content states and their creative contexts;
- provenance and relevant timestamps;
- records for imports and AI suggestions;
- application configuration that is appropriate for database storage;
- references and metadata for privately stored objects;
- export, backup, and restoration records where appropriate;
- authorization-related application records, excluding secrets that require a separate protected mechanism.

The database representation must preserve the distinctions required by the product model. It must not flatten authored, imported, and AI-generated material into indistinguishable content.

The final database product, data representation, indexing approach, and revision strategy remain undecided.

### Private Object Storage

Private object storage holds binary or large objects that are unsuitable for the primary database.

In Version 1, its use should be limited to demonstrated needs. It may hold:

- generated export packages;
- backup artifacts or staged backup data;
- supported attachments if such attachments are included in the approved Version 1 design;
- future artwork, maps, and other private media.

Objects must not be publicly addressable by default. Access must be mediated by authenticated, authorized application behavior or by short-lived, narrowly scoped access mechanisms.

The database and object store must use stable references so exports, backups, verification, and restoration can preserve the relationships between metadata and stored objects. Object storage must not become an undocumented secondary archive whose contents cannot be reconciled with database records.

### Background Job Runner

The background job runner performs bounded work that should not block an interactive request or that benefits from controlled retry and status reporting.

Candidate responsibilities include:

- creating exports;
- creating and verifying backups;
- performing restoration validation;
- processing supported private objects;
- running bounded indexing work;
- invoking longer-running AI operations through the AI gateway;
- running future synchronization tasks through integration adapters.

Jobs must carry only the authority and data needed for their task. They must be idempotent or otherwise safe against duplicate execution where practical. Retries must not silently duplicate content, overwrite authoritative material, promote content states, or repeat externally visible actions without safeguards.

The application must record enough job state to distinguish pending, running, succeeded, failed, and safely retryable work. The final queue or scheduling mechanism remains undecided.

### AI Gateway

The AI gateway is the sole application boundary for communication with external model providers.

Its responsibilities include:

- accepting only explicitly invoked, supported AI tasks;
- enforcing task-specific context limits;
- receiving context selected or approved through application rules;
- making the included sources visible or clearly understandable to the author;
- excluding unrelated creative material;
- applying provider-specific request and credential handling;
- enforcing configured usage and cost constraints;
- recording appropriate request and output provenance without creating unsafe logs;
- translating provider responses into an internal, provider-independent result;
- classifying generated output as an AI suggestion;
- returning failures without changing source content.

The gateway must not grant an AI provider direct access to the primary database, private object storage, filesystem, or full creative archive. A model provider receives only the bounded content included in an individual authorized request.

Provider retention, training use, geographic processing, model availability, content limits, cost controls, and failure behavior must be evaluated before selecting a provider.

### Export and Backup Subsystem

The export and backup subsystem serves two related but distinct purposes.

**Export** produces an author-facing, documented representation of supported creative content that can be inspected and used without the running application.

**Backup** captures enough application state to restore a working Strange Novelty workspace.

Its responsibilities include:

- selecting the complete and correct records for each operation;
- preserving hierarchy, content, states, links, backlinks or their derivable relationships, and provenance;
- including referenced private objects when required;
- producing manifests describing contents, format version, and relevant creation metadata;
- performing structural and integrity checks;
- reporting verification results clearly;
- preventing incomplete artifacts from being represented as verified;
- supporting documented restoration procedures;
- maintaining compatibility or migration rules for supported backup versions;
- avoiding exposure of secrets that are not required for restoration.

Export and backup artifacts contain private content and must receive protections appropriate to the primary archive.

### Future Integration Adapters

Future integration adapters provide isolated boundaries for approved external services such as document storage, document editing, email, or publishing systems.

Each adapter must:

- request the least external authority required for its workflow;
- define the direction of data flow;
- identify the source of truth for synchronized data;
- preserve provenance for imported or synchronized material;
- surface conflicts rather than silently resolving them;
- make destructive or publishing actions explicit;
- handle revocation, expiration, disconnection, and partial failure;
- prevent an external service from becoming the sole custodian of the archive;
- preserve export, backup, and restoration capabilities without the integration.

Version 1 does not require these adapters. Their boundary is defined now to prevent later integrations from bypassing the application server, domain rules, or privacy model.

## Trust Boundaries

### Authentication and Authorization Boundary

The browser, network, and unauthenticated requests are outside the trusted application boundary.

Every request for private content or state-changing behavior must be authenticated and authorized by the application server. Client-side state is not proof of identity or permission.

Version 1 has one authorized human user, but the architecture must still distinguish among:

- unauthenticated access;
- the authenticated author;
- application-controlled background processes;
- AI-provider requests;
- future integration processes;
- operational or recovery access.

Background processes and adapters must receive narrowly scoped service authority rather than inheriting unrestricted author access.

Authentication mechanisms, credential storage, session duration, account recovery, and administrative recovery remain to be selected and documented.

### Private Content Boundary

The primary database, private object storage, exports, backups, and any retained AI inputs or outputs are inside the private content boundary.

Private content must not be exposed through:

- public object addresses;
- unauthenticated application routes;
- client-visible secrets;
- source control;
- operational logs;
- error reports;
- analytics payloads;
- broadly scoped AI requests;
- unapproved external integrations.

Content crossing this boundary must do so for an explicit purpose under an authenticated and authorized workflow. Exports and backups remain private after leaving the live system.

### AI-Provider Boundary

The AI provider is outside the trusted private application boundary.

Only the AI gateway may transmit content across this boundary. Each transmission must be associated with:

- an explicitly invoked task;
- a bounded source set;
- a reason each source is relevant or a clear description of the selection rule;
- the applicable privacy and retention policy;
- a result classified as an AI suggestion;
- sufficient provenance to identify the operation.

The provider must never be treated as a source of canonical truth or as durable primary storage.

### External Integration Boundary

Every external integration is outside the trusted application boundary, even when operated by a familiar provider or owned by the author.

Integration credentials, synchronization behavior, imported data, conflicts, provider outages, and remote deletions must be handled as boundary concerns. No integration may bypass state classification, provenance, authorization, or author approval rules.

### Operational Logging Boundary

Operational logging is separate from the creative data store.

Logs may contain technical events needed to operate, secure, and diagnose the application, such as:

- timestamps;
- request or correlation identifiers;
- component and operation names;
- status codes;
- latency;
- job state;
- coarse error categories;
- authentication and security events appropriate for review.

Logs must not contain scene text, story notes, AI prompts or responses, object contents, credentials, session tokens, external-service tokens, backup contents, or other unnecessary private material.

Where identifiers are necessary, logging should minimize their sensitivity and retention. Access, retention, redaction, and disposal rules must be defined before implementation.

## Data Flow Between Components

### Interactive Read and Write Flow

1. The author uses the browser client to sign in and request or change content.
2. The browser sends the request to the application server over a protected connection.
3. The application server authenticates the session and authorizes the operation.
4. The server validates domain rules, including hierarchy, state-transition, provenance, and relationship rules.
5. The server reads or writes the primary database and, when needed, mediates private object storage access.
6. The server returns only the data required for the current browser view.
7. The browser presents the result, including relevant state, provenance, hierarchy, and relationship context.

### Background Work Flow

1. An authorized application action creates a bounded job description.
2. The application records the job and supplies only the required authority and references.
3. The background job runner retrieves the necessary data through controlled application or storage interfaces.
4. The runner performs the operation with safe retry behavior.
5. Results and status are persisted.
6. The browser obtains status through the application server.

A job must not convert imported content or an AI suggestion to canon, publish material, or perform another authority-changing action without an explicit author action represented in the application.

### AI Assistance Flow

1. The author explicitly invokes the supported AI capability.
2. The application assembles a task-specific candidate context using explicit selections, links, metadata, or a clearly described search.
3. The browser shows or clearly describes the sources that will be included.
4. After author initiation, the application server sends the bounded task to the AI gateway.
5. The AI gateway transmits only the approved content and necessary instructions to the selected provider.
6. The provider returns a result to the gateway.
7. The gateway normalizes the result and attaches relevant provenance.
8. The application stores or presents the result as an AI suggestion.
9. The author may reject, retain, revise, or intentionally reclassify the suggestion through ordinary domain rules.

Failure at any stage must leave authoritative source content unchanged.

### Export Flow

1. The author explicitly requests an export and selects its supported scope.
2. The application authorizes the request and records the operation.
3. The export subsystem reads a consistent representation of the selected data and referenced objects.
4. It creates a documented artifact and manifest.
5. It validates the artifact sufficiently to detect missing or malformed expected content.
6. The application reports completion and provides private, authorized access to the artifact.
7. The artifact can be inspected without relying on the running application.

### Backup and Restoration Flow

1. An authorized action or approved schedule requests a backup.
2. The backup subsystem captures a consistent set of required database state, private objects, and restoration metadata.
3. It creates a manifest and integrity information.
4. Verification confirms that expected components exist and pass defined checks.
5. The verified artifact is stored in an appropriately protected location separate enough from the live system to support recovery.
6. Restoration occurs into an isolated or deliberately prepared target.
7. The restore process validates format compatibility and integrity before activation.
8. Representative application checks confirm that hierarchy, content, states, links, provenance, and required objects remain usable.
9. Restoration is not considered proven until the restored workspace has passed the documented test.

## Deployment Shape for a Private Single-User Web Application

Version 1 should use the smallest deployment shape that can securely and reliably support the required boundaries.

Conceptually, the deployment consists of:

- one private browser-facing application endpoint;
- one application server deployment;
- one authoritative primary database;
- private object storage where required;
- one background job execution environment, which may share an operational deployment with the application while remaining logically separate;
- outbound access from the AI gateway to an approved model provider;
- protected locations for exports and backups;
- operational logging and monitoring that exclude creative content.

The deployment may use one host or a small set of managed services, provided the logical boundaries and recovery requirements remain intact. A distributed or microservice architecture is not required for a solo-user Version 1 system.

The browser-facing endpoint must use protected transport and must not expose the database, object storage, job control interfaces, administrative interfaces, or internal service credentials directly.

The application should remain operable without future integrations. Temporary AI-provider unavailability should affect only the AI capability, not ordinary access to the creative archive.

The final hosting model, operator, network exposure, service topology, cloud provider, and degree of self-hosting remain open decisions.

## Version 1 Architecture

Version 1 is a modular private web application, not a general-purpose platform.

Its active architecture supports:

- secure access for one authorized author;
- worlds, series, books, chapters, and scenes;
- scene drafting and revision;
- characters and locations;
- supported links and backlinks;
- required content states and contextual classification;
- basic authored, imported, and AI-generated provenance;
- search and navigation;
- one narrow, explicitly invoked AI capability;
- documented export;
- backup creation and verification;
- documented and tested restoration.

The application server is the center of domain rules and security enforcement. The primary database is the authoritative structured store. Private object storage is introduced only where actual Version 1 data requires it. The job runner handles bounded asynchronous work. The AI gateway prevents model-provider details and external trust assumptions from spreading through the application. Export and backup behavior is designed as a product capability from the beginning.

Version 1 should favor a cohesive deployable application with clear internal modules. Components may be logically distinct without requiring independently deployed services. Separation into additional processes or services should occur only when security, reliability, workload, or operational evidence justifies it.

Version 1 does not include public sharing, teams, collaborative editing, arbitrary plugins, unrestricted entity types, comprehensive continuity analysis, general external synchronization, publishing automation, or autonomous AI behavior.

## Reliability and Recovery Expectations

The system should prioritize data durability and understandable failure behavior over uninterrupted availability.

Version 1 should meet these conceptual expectations:

- acknowledged content changes are durably stored according to a documented persistence model;
- failed requests do not appear successful;
- retries do not create unexplained duplicate records or repeat unsafe actions;
- partial failures are detectable and reported;
- background jobs expose meaningful status;
- AI or integration outages do not prevent ordinary access to locally authoritative content;
- loss of generated indexes or other derived data does not imply loss of authoritative content;
- exports and backups are not marked complete until required validation succeeds;
- restoration can rebuild a usable workspace from a supported verified backup;
- common editing mistakes have an appropriate history, versioning, undo, or restoration path;
- operational recovery procedures are documented and tested in proportion to risk;
- corruption, missing objects, incompatible backup versions, and incomplete restores fail visibly.

Specific availability targets, recovery time objectives, recovery point objectives, revision retention periods, and backup schedules remain open decisions.

## Export, Backup, Verification, and Restoration Responsibilities

### Export Responsibilities

The application must:

- define the scope and version of each supported export format;
- produce useful, documented output;
- preserve essential hierarchy, content, states, links, and provenance;
- include or reference supported private objects in a portable way;
- allow inspection without the running application;
- avoid including credentials, session material, or unrelated operational data.

### Backup Responsibilities

The application and its operator must:

- identify every component required for a complete recovery;
- capture database state and required private objects consistently;
- protect backup artifacts as private creative content;
- store backups so a failure of the live deployment does not necessarily destroy all recovery copies;
- retain the information needed to interpret the backup format;
- define rotation and retention without silently eliminating the last usable recovery point.

### Verification Responsibilities

Backup verification must:

- confirm that an artifact was created;
- validate its manifest and expected components;
- check integrity using a defined mechanism;
- detect missing referenced objects where applicable;
- record the verification result and time;
- distinguish structural verification from a successful restoration test.

An existence check alone is not sufficient verification.

### Restoration Responsibilities

Restoration must:

- validate the backup before applying it;
- avoid overwriting a working archive without an explicit, protected recovery procedure;
- handle supported format versions or fail with a clear compatibility error;
- restore required database state and private objects;
- rebuild derived state where appropriate;
- confirm the usability of representative hierarchy, content, states, links, backlinks, and provenance;
- be documented sufficiently for the operator to execute during an actual recovery.

A backup capability is not complete until restoration has been successfully tested with representative data.

## Security Invariants

The following conditions must remain true regardless of the selected technology stack:

- Unauthenticated users cannot access private creative content.
- Authorization is enforced by the application server for every private read and state-changing operation.
- Browser code is never trusted as the sole enforcement point.
- Private content is protected in transit and with appropriate storage controls.
- Creative content, credentials, secrets, tokens, exports, backups, databases, and private objects are never committed to the repository.
- Private story files remain under the designated private-data boundary and outside version control.
- Application secrets are not exposed in client-visible configuration or logs.
- Operational logs do not contain creative content, AI prompt or response bodies, credentials, tokens, or backup contents.
- Private objects are not publicly accessible by default.
- AI providers receive only the context needed for an explicitly invoked task.
- AI providers do not receive direct access to the primary database, object storage, or creative archive.
- AI output is identified as an AI suggestion and cannot become canon automatically.
- Imported content remains identifiable as imported until explicitly reviewed.
- Authority-changing actions are intentional and attributable to the author.
- External integrations use least privilege and cannot silently overwrite, delete, publish, or reclassify authoritative content.
- No external provider is the sole custodian of the author’s archive.
- Exports and backups are protected as private content.
- Recovery operations are explicit and protected against accidental overwrite.
- Security failures fail closed where private content could otherwise be exposed.
- The old Story Engine remains reference-only and is never modified by Strange Novelty work.

## Explicit Non-Decisions

This overview intentionally leaves the following choices open:

- the browser framework or rendering approach;
- the application-server framework and programming language;
- the final database product;
- the database hosting model;
- the detailed database schema and content representation;
- the scene revision, history, or undo implementation;
- the authentication mechanism or provider;
- credential and account-recovery implementation;
- the session mechanism and expiration policy;
- the authorization implementation;
- the queue, scheduler, or background-job product;
- the object-storage product or vendor;
- whether Version 1 needs object storage beyond export and backup artifacts;
- the AI provider, model, and model-access mechanism;
- the exact Version 1 AI task;
- AI retention, cost, and usage limits pending provider evaluation;
- the search engine and indexing approach;
- the export format;
- the backup format, destination, schedule, and retention policy;
- integrity-checking and backup-encryption mechanisms;
- hosting location and cloud provider;
- self-hosted versus managed infrastructure;
- deployment tooling and service topology;
- logging, monitoring, and alerting products;
- exact availability, recovery-time, and recovery-point targets;
- future integration providers and synchronization models.

These choices must be made only after the relevant product, data, security, AI-context, integration, operational, and recovery requirements are documented. Significant durable choices should be recorded in architecture decision records.

## Future Evolution

Future evolution should extend the stable Version 1 boundaries instead of bypassing them.

Possible evolution includes:

- richer structured entities and provenance;
- separate modeling of story chronology, reader revelation, and character knowledge;
- review-oriented continuity tools;
- stronger search and task-specific context retrieval;
- additional bounded AI assistance;
- private artwork and map storage;
- generators whose outputs begin as AI suggestions;
- external document, storage, and email integrations;
- manuscript compilation and publishing-oriented exports.

Growth may justify separating logical components into independently deployed services, adding specialized indexes, expanding object storage, or introducing more sophisticated job orchestration. Such changes should be driven by observed workload, security needs, failure isolation, or maintainability—not by an assumption that a larger architecture is inherently better.

Every future capability must continue to preserve:

- authorial control;
- contextual content states;
- provenance;
- private-by-default behavior;
- narrow external access;
- useful exports;
- complete backups;
- tested restoration;
- independence from any single external provider.

External integrations must remain replaceable and disconnectable. AI gateways should support provider evolution without allowing provider-specific concepts to become the application’s core data model. Derived indexes, generated summaries, and external copies must remain rebuildable or subordinate to the primary archive.

## Open Questions

The following questions must be resolved in later architecture documents or decision records before implementation depends on them:

1. Where will the private application run, who will operate it, and how will the author securely reach it?
2. What network exposure is acceptable for a private single-user application?
3. Which authentication and account-recovery model best fits secure single-user operation?
4. How will sessions be created, protected, expired, revoked, and recovered?
5. How will secrets, encryption material, database credentials, and external-service tokens be stored and rotated?
6. What is the authoritative representation of scene content, structured entities, links, contextual states, and provenance?
7. What revision or history model provides sufficient recovery from editing mistakes?
8. What concurrency assumptions should apply if the author opens the workspace in multiple browser tabs or devices?
9. Which data belongs in the primary database, and which data, if any, belongs in private object storage in Version 1?
10. How will backlinks be represented or derived while remaining consistent with links?
11. What initial search behavior and indexing strategy satisfy Version 1 without prematurely introducing semantic search?
12. What is the one bounded AI capability for Version 1?
13. How will AI context be selected, limited, previewed or described, and associated with the resulting suggestion?
14. Which AI-provider privacy, retention, training-use, geographic, cost, and availability terms are acceptable?
15. What AI request and response information must be retained for useful provenance, and what must not be retained?
16. What useful, documented export format best preserves hierarchy, content, states, links, and provenance?
17. What constitutes a complete backup of the Version 1 system?
18. Where will backups be stored so they survive loss of the live deployment?
19. How will backups be protected, versioned, verified, rotated, and restored?
20. What representative restoration test must pass before Version 1 is accepted?
21. What recovery point and recovery time expectations are appropriate for the author’s workflow?
22. What operational events are needed for diagnosis and security review without exposing creative content?
23. How long should operational logs and job records be retained?
24. Which failures should trigger alerts in a low-maintenance single-user deployment?
25. Does Version 1 support any bounded import workflow, and if so, how is imported authority and provenance preserved?
26. Which conceptual components should share a deployment initially, and which require process or service isolation?
27. What is the smallest implementation milestone that proves secure access, durable storage, basic navigation, and recovery?
28. Which technology stack best satisfies these documented constraints once the remaining architecture foundations are approved?
