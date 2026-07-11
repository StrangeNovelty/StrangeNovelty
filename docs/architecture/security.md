# Strange Novelty Version 1 Security Architecture

## Purpose and Scope

This document defines the proposed security architecture for Version 1 of Strange Novelty, a private web application for one author and artist. It establishes requirements and boundaries without selecting a final framework, authentication provider, hosting provider, database, object store, encryption product, secret manager, or cloud vendor.

Security protects more than conventional personal data. Unpublished manuscripts, notes, artwork, research, relationships, provenance, AI inputs and outputs, exports, and backups may have personal, creative, reputational, or commercial value. A single user reduces collaboration complexity; it does not make compromise, data loss, malicious input, credential theft, provider exposure, or operational mistakes low-risk.

Version 1 has one authorized human owner. Only that authenticated owner may access creative content. Application-controlled processes may act only within narrowly defined service authority. There are no public workspaces, public sharing links, guest roles, team roles, or anonymous creative-content routes.

## Security Goals

Version 1 should:

- preserve the confidentiality of creative content and sensitive metadata;
- preserve the integrity of content, states, provenance, links, revisions, audit records, exports, and backups;
- keep the workspace available and recoverable after common failures and security incidents;
- authenticate the owner securely and authorize every private operation server-side;
- minimize the data and authority exposed to browsers, background jobs, AI providers, integrations, operators, and diagnostic systems;
- make security-sensitive, destructive, and authority-changing actions explicit and attributable;
- fail closed when identity, permission, integrity, or request validity cannot be established;
- support secure export, backup, verification, migration, and restoration without weakening normal controls;
- keep security controls understandable and operable for a solo creator; and
- preserve authorial control: no compromise of a peripheral service should silently change creative authority or canon.

## Security Assumptions

Version 1 is based on these assumptions:

- One human owner is authorized to use the Workspace, but the application may be reached from multiple browsers, tabs, or devices.
- The browser, client device, network, uploaded files, imported content, AI providers, and future integrations are not inherently trusted.
- The application server is the central authentication, authorization, validation, and domain-policy enforcement boundary.
- Server infrastructure, database, object storage, backups, and administrative paths require explicit protection and limited operator access.
- Dependencies and deployment systems may be compromised and must not be trusted without verification and containment.
- An attacker may know that the application exists and may target it despite its single-user design.
- The owner may make mistakes, lose a credential or device, import hostile content, or initiate an unsafe restoration.
- External providers may retain, inspect, process, disclose, or lose transmitted data according to their own controls and terms.
- No security control eliminates the need for tested backups, restoration, incident response, and credential rotation.

The deployment location, operator, exposure to the public internet, and accepted recovery objectives remain open. Those decisions may strengthen requirements but must not weaken the invariants in this document.

## Threat Model

### Threat actors

Relevant threat actors include:

- unauthenticated internet or network users;
- attackers using stolen, guessed, reused, phished, or recovered credentials;
- malware or a malicious browser extension on an authorized device;
- an attacker exploiting application, dependency, server, database, object-storage, or deployment vulnerabilities;
- malicious content embedded in uploads, archives, HTML, Markdown, documents, or imported records;
- compromised AI providers, integrations, dependencies, build systems, or operator credentials;
- external service personnel or systems with access beyond the intended request scope; and
- the authenticated owner acting accidentally through a confusing, stale, forged, or replayed request.

### Threats in scope

Version 1 must account for:

- unauthorized reading, enumeration, search, download, export, or inference of private content;
- account takeover, session theft, fixation, replay, or failure to revoke access;
- broken access control, insecure direct object references, and cross-Workspace access;
- injection, cross-site scripting, cross-site request forgery, server-side request forgery, path traversal, and unsafe deserialization or parsing;
- malicious or oversized uploads, archive bombs, active document content, and unsafe rendering;
- secret exposure through source control, browser bundles, logs, errors, process output, build artifacts, or backups;
- excessive AI or integration context, unauthorized tool access, prompt injection, and provider retention;
- accidental or malicious deletion, overwrite, canon promotion, provenance loss, or restoration of corrupted data;
- public object URLs, misconfigured storage, database exposure, or overly broad service credentials;
- sensitive-data leakage through logs, analytics, crash reports, traces, alerts, caches, or telemetry;
- dependency substitution, compromised packages, vulnerable transitive dependencies, and build or deployment tampering; and
- denial of service or cost abuse against authentication, uploads, exports, AI operations, or background work.

### Threats not eliminated by Version 1

Version 1 cannot fully protect content displayed on a device that is already controlled by an attacker, prevent the authorized owner from intentionally copying content elsewhere, or guarantee an external provider will never be compelled or compromised. These limitations do not justify weakening server, storage, provider-selection, or data-minimization controls.

## Protected Assets

Protected assets include:

- Workspace records, scenes, revisions, characters, locations, links, backlinks, states, contexts, provenance, and lifecycle history;
- manuscripts, notes, research, correspondence, artwork, maps, attachments, and other private objects;
- search indexes, staged imports, AI requests, AI suggestions, and retained provider metadata that reveal private content;
- account identifiers, password verifiers, MFA material, recovery material, sessions, cookies, and security events;
- database credentials, API keys, integration tokens, encryption keys, signing keys, deployment credentials, and other secrets;
- exports, backups, database snapshots, manifests, integrity data, and restoration material;
- audit records whose integrity establishes author approval or authority changes;
- application source, build and deployment configuration, dependency metadata, and administrative interfaces; and
- availability, backup usability, and the owner’s ability to recover or leave with the archive.

Metadata can itself be sensitive. Titles, identifiers, filenames, timestamps, object sizes, relationship graphs, prompt manifests, and error context must not be assumed harmless.

## Trust Boundaries

### Browser and network boundary

The browser and all request data are outside the trusted server boundary. Client-side hiding, route guards, disabled controls, local state, and obscured identifiers are usability features, not authorization. The server must authenticate, authorize, validate, and constrain every private read and state-changing request.

### Application and storage boundary

The application server mediates access to the primary database and private object storage. Neither storage system may be directly reachable from an unauthenticated client. Storage credentials remain server-side and are scoped to the minimum required operations.

### Background-process boundary

Job runners, importers, indexers, exporters, backup processes, and restoration tools are distinct principals. A job receives a bounded task, Workspace, required references, and limited authority; it does not inherit an unrestricted owner session.

### AI-provider boundary

Every AI provider is outside the private application boundary. Content crosses this boundary only through the AI gateway for an explicitly invoked, supported task with narrow, deliberate context. Providers never receive direct database, object-store, filesystem, or workspace access.

### External-integration boundary

Every future integration remains external even when the account belongs to the owner. Each adapter requires explicit authorization, least-privilege permissions, bounded data flow, revocation, provenance, and failure handling.

### Operational and administrative boundary

Logs, telemetry, deployment systems, support tools, administrative shells, and recovery environments are separate security domains. Operational access does not imply routine permission to inspect creative content.

### Export, backup, and restoration boundary

Exports and backups remain sensitive after leaving the live application. Restoration crosses a high-risk boundary from an artifact into authoritative storage and therefore requires independent integrity, compatibility, authorization, validation, and migration checks.

## Authentication Requirements

- Every route, query, API operation, download, object access, export, backup action, and administrative workflow that can reveal or affect private state must require authenticated identity unless it is deliberately limited to the sign-in or recovery flow.
- Version 1 supports one enrolled owner identity and must not expose self-service public registration.
- Initial enrollment must be controlled so an unauthenticated visitor cannot claim the owner account.
- Authentication must use a well-reviewed, current mechanism appropriate to the eventual deployment and must resist credential stuffing, brute force, enumeration, replay, and downgrade.
- Authentication errors should not reveal whether an account, recovery method, or credential factor exists.
- Sign-in attempts require rate limiting and, where justified, progressive delay or temporary throttling. Controls must avoid creating an easy permanent lockout attack.
- Successful and failed authentication, recovery initiation and completion, factor changes, and session revocation should create privacy-conscious security events.
- Any authentication provider remains a trust dependency and must not gain access to creative content merely by authenticating the owner.

The final authentication provider and mechanism are explicitly undecided.

## Authorization Requirements

- Authorization is enforced server-side on every private read, search, write, delete, download, export, backup, restore, AI, integration, and administrative operation.
- The authenticated owner may act only on records belonging to the authorized Workspace. Workspace ownership must be verified using authoritative identifiers, never inferred from the browser, path, display name, or hidden field.
- Queries must be scoped by Workspace before data is returned or modified. Object identifiers alone never confer access.
- Background jobs and service components use separate, narrowly scoped authority tied to a specific operation; they do not reuse owner credentials or unrestricted storage credentials.
- AI providers and integrations have no implicit owner authority. Returned content is untrusted input and passes ordinary validation, provenance, state, and approval rules.
- Authority-changing operations, including Canon promotion, destructive purge, credential changes, integration grants, export, backup deletion, and restoration activation, require explicit server-validated intent and any risk-appropriate reauthentication or confirmation.
- Authorization failures must not disclose whether a target private record exists.
- Deny is the default for new routes, record types, background tasks, and integration capabilities.

## Session Management

Sessions must:

- be created only after successful authentication and renewed after authentication or privilege-sensitive changes to prevent fixation;
- use high-entropy, unguessable identifiers or equivalent protected session state;
- be transmitted only over protected transport in cookies or another mechanism designed to resist browser token theft;
- use cookie protections appropriate to the selected architecture, including `Secure`, `HttpOnly`, and a restrictive `SameSite` policy where cookies are used;
- never place bearer credentials in URLs, logs, page source, analytics, or persistent browser storage;
- have documented idle and absolute expiration appropriate to a private creative workspace;
- support explicit sign-out, server-side invalidation, revocation of all sessions, and revocation after password, factor, recovery, or suspected-compromise events;
- rotate or reissue sensitive session material at defined boundaries;
- avoid extending sessions indefinitely through background traffic alone; and
- record enough metadata to let the owner identify and revoke active sessions without collecting unnecessary device data.

Sensitive actions may require recent authentication even within a valid session. Concurrent tabs and devices must not bypass concurrency, authorization, or revocation checks.

## Password and Credential Handling

If passwords are used:

- password verifiers must be produced with a current, memory-hard password-hashing construction and unique salts using parameters reviewed for the deployment;
- plaintext passwords, reversible password encryption, security questions, password hints, and password logging are prohibited;
- the application should permit long passphrases and password-manager use without arbitrary composition rules that reduce usability;
- breached or trivially weak passwords should be rejected using a privacy-preserving check where feasible;
- verification and reset endpoints require throttling and generic responses; and
- password changes revoke or deliberately review existing sessions and recovery material.

Application credentials, database credentials, API keys, service tokens, signing keys, and encryption keys are not user passwords. They must be separately scoped, stored, rotated, and revoked. Credentials and secrets must never be exposed to the browser or committed to Git.

## Multi-Factor Authentication Considerations

Version 1 must evaluate MFA before authentication is selected. MFA is strongly preferred when the application is reachable from the public internet, when the authentication provider supports it safely, or when administrative access can expose the archive.

The preferred factor should resist phishing where operationally practical. If time-based codes are supported, seed material and recovery codes are secrets. SMS or email factors, if considered, require an explicit assessment of account takeover and recovery dependencies.

MFA enrollment, replacement, disabling, and recovery are high-risk operations. They require recent authentication, explicit confirmation, security-event recording, and session review. Recovery codes must be shown narrowly, stored only as protected verifiers where possible, and never logged. The final MFA method and whether it is mandatory for the owner remain open decisions.

## Account Recovery

Account recovery must restore access without becoming an authentication bypass.

- Recovery must prove control through a separately protected channel or pre-established recovery material.
- Recovery tokens must be random, single-use, short-lived, stored as protected verifiers where feasible, and invalidated after use or replacement.
- Recovery responses must resist account enumeration.
- Completion should revoke or review active sessions, invalidate superseded reset material, and create a security event.
- Recovery must not disclose creative content, secrets, backups, or credential metadata to unauthenticated requesters.
- Administrative recovery must be documented, deliberately invoked, independently authenticated, and unable to silently change Workspace ownership or provenance.
- The recovery design must address loss of both the primary credential and MFA factor without relying on undocumented operator knowledge.

The final recovery channel, identity proof, delay, and emergency procedure are undecided and must be tested before Version 1 acceptance.

## Transport Security

- All browser, API, administrative, storage, database, AI-provider, integration, backup-transfer, and restoration-management connections carrying sensitive data must use authenticated encryption in transit.
- Plaintext application access must be disabled or redirected without accepting credentials or private content over the plaintext connection.
- Transport configuration must use supported protocol versions, current cipher guidance, valid certificate verification, and secure proxy forwarding rules.
- Strict transport enforcement should be enabled after confirming the deployment and recovery implications.
- Internal network location is not a substitute for transport protection or authentication.
- Service-to-service identities and certificate or key rotation must be documented where separate services are deployed.

## Data-at-Rest Protection

Creative data, credentials, tokens, retained AI material, exports, backups, logs, and snapshots require protection at rest proportional to their sensitivity and exposure.

At minimum:

- storage must not be public by default;
- access must be restricted to the application and narrowly authorized operators or service principals;
- platform or volume encryption should protect lost media, snapshots, and decommissioned hardware;
- backups and exports require independent protection after download or replication;
- encryption keys must be separated from the protected data to the degree supported by the selected deployment;
- key access, rotation, recovery, and loss scenarios must be documented; and
- deletion and retention behavior must address replicas, caches, snapshots, backups, and provider limitations honestly.

At-rest encryption does not replace authorization, query scoping, application validation, or protection from a compromised running service. The final encryption product and any field-level encryption are undecided.

## Database Protection

- The database must not be directly exposed to browsers or the public internet.
- Network access must be restricted to required application, migration, backup, and restoration paths.
- Application credentials must have the minimum database privileges needed at runtime; schema administration, migration, backup, and restoration privileges should be separated where practical.
- Production credentials must not be shared with development, test, analytics, or local tooling.
- Queries must be parameterized or generated through mechanisms that preserve parameter separation; string-built queries from untrusted input are prohibited.
- Workspace ownership, referential integrity, concurrency checks, and destructive-operation protections should be reinforced at multiple appropriate layers.
- Database errors returned to the browser must not expose queries, schema, connection details, content, or secrets.
- Copies, snapshots, replicas, diagnostic dumps, and local extracts are sensitive databases and receive the same handling rules.
- Backup and restore access must not provide a less-protected path to the database.

The final database, hosting model, credential mechanism, and encryption details remain open.

## Private Object-Storage Protection

- Objects are private by default and must not have predictable public URLs or public bucket/container access.
- The application authorizes every object operation against Workspace ownership and object metadata.
- Direct browser transfer, if later used, must rely on short-lived, single-purpose, narrowly scoped grants constrained by object, operation, size, content expectations, and expiration.
- Object names and paths must not be derived unsafely from supplied filenames or permit traversal, overwrite, or cross-Workspace collision.
- Download responses should use safe content types, disposition headers, filename handling, cache controls, and anti-sniffing protections.
- Storage credentials remain server-side, scoped, rotated, and excluded from source control and client configuration.
- Orphaned objects, missing objects, partial uploads, retention, deletion, export, backup, and restoration must be detectable and reconcilable with authoritative database records.
- Provider access logs and object metadata must avoid unnecessary creative filenames or content.

## Secret and Environment-Variable Management

Secrets include credentials, API keys, tokens, signing material, encryption keys, cookie secrets, database passwords, webhook secrets, recovery material, and any value that grants access.

- Secrets must never be committed to Git, placed in browser-visible environment variables, embedded in client bundles, printed in build output, or included in exports and routine backups unless a separately defined recovery design requires protected key material.
- Environment variables are a delivery mechanism, not automatically a safe secret store. Process inspection, crash reporting, deployment consoles, and child-process inheritance must be considered.
- Development, test, staging, and production use separate credentials and least-privilege scopes.
- Secret access is limited to the components that require it, with separate secrets for materially different privileges.
- Rotation, revocation, expiration, emergency replacement, and dependent-service restart behavior must be documented and tested.
- Logs and errors must redact secrets by construction, not depend solely on post-processing.
- Example configuration contains placeholders only. Local secret-bearing files remain ignored and outside version control.

The final secret manager and environment configuration system are explicitly undecided.

## Browser and Client-Side Security

- The browser receives only the content and capabilities required for the current authorized view.
- No application, storage, integration, AI, or administrative secret may be shipped to client code.
- Server authorization must not depend on hidden UI controls, route secrecy, JavaScript checks, or client-provided ownership fields.
- Sensitive content should not be placed in URLs, referrers, page titles, notifications, analytics, or persistent browser storage without a documented need.
- Browser caching of authenticated content must use a deliberate policy, especially for downloads, exports, backups, and shared-device risk.
- A restrictive content security policy, controlled script sources, framing restrictions, MIME sniffing protection, referrer policy, and permissions policy should reduce browser attack surface.
- Third-party scripts, fonts, analytics, editors, and asset hosts are external data recipients and should be avoided unless explicitly reviewed and necessary.
- Rich content must be rendered through safe encoders or a narrowly configured sanitizer; raw imported HTML must never be trusted.
- The product should provide clear sign-out and session-revocation behavior for lost or shared devices.

## CSRF, XSS, Injection, and Request-Forgery Protections

### Cross-site request forgery

State-changing requests require defenses appropriate to the session design: restrictive cookie policy, unpredictable anti-CSRF tokens or equivalent origin-bound protection, and Origin or Referer validation where reliable. Safe HTTP methods must not change state. High-impact actions require explicit intent and must not be triggerable through a simple cross-origin request.

### Cross-site scripting

All untrusted text is output-encoded for its rendering context. HTML, Markdown, document previews, filenames, AI output, import warnings, and provenance fields are untrusted. Sanitization must use a maintained allowlist policy, remove active content and dangerous URLs, and be followed by safe rendering. A content security policy provides defense in depth but does not replace encoding and sanitization.

### Injection

Database, search, command, template, path, header, archive, and structured-data operations must preserve a strict boundary between instructions and data. Use parameterized interfaces and allowlisted operation choices. Untrusted values must not be interpolated into shell commands, queries, templates, file paths, or dynamic code. Unsafe evaluation and deserialization are prohibited.

### Server-side request forgery

The server must not fetch arbitrary user- or imported-content URLs. Any supported fetch uses an allowlisted purpose and protocol, URL parsing, DNS and redirect checks, connection and response limits, and blocking of loopback, link-local, private, metadata-service, and internal administrative destinations. Redirects must be revalidated at every hop. Provider callbacks and webhooks require authentication and replay protection.

## File-Upload and Import Safety

All uploads and imported HTML, Markdown, documents, archives, and records are untrusted, including files created by the owner.

- Version 1 should accept only formats required by approved workflows, with documented size, count, nesting, and processing limits.
- File type must be verified using content-aware checks; supplied extension and MIME type are hints only.
- Filenames are display metadata, not storage paths, commands, or trusted content types.
- Uploads should be staged outside authoritative content, assigned server-controlled identifiers, scanned or inspected as appropriate, and made available only after validation succeeds.
- Active content, macros, scripts, remote references, embedded executables, unsafe links, metadata, and parser-specific features must be removed, rejected, or rendered inert.
- Archives require limits on entries, expanded size, compression ratio, path depth, nesting, symbolic links, special files, and traversal. Extraction occurs in an isolated, bounded location.
- Parsers and converters should run with limited CPU, memory, time, filesystem, network, and process privileges.
- Imported content remains Imported content with provenance until explicit author review; parsing does not grant authority or Canon status.
- Import must not overwrite by name, create cross-Workspace links, hide partial failure, or bypass ordinary validation and concurrency rules.
- Malicious content must remain unable to execute when previewed, exported, restored, indexed, sent to AI, or displayed in an error.

Retention and disposal of rejected, quarantined, staged, and partially imported files must be defined before implementation.

## AI-Provider Data Exposure

External AI requests deliberately cross a trust boundary and require explicit author initiation.

- The AI gateway is the only component permitted to send private content to a model provider.
- Each supported task defines its purpose, permitted source types, selection rule, maximum context, excluded categories, output treatment, and failure behavior.
- Context uses the narrowest deliberate source set needed for the task. Entire directories, databases, workspaces, backups, or unrestricted retrieval are prohibited.
- Before submission, the author must see the selected sources or receive a clear, accurate description of the selection rule and included scope.
- Provider credentials remain server-side. Providers receive no direct tools or credentials for database, object-storage, filesystem, search, export, backup, or integration access.
- Prompt injection in creative or imported content is treated as untrusted data, not authority to expand context, call tools, reveal secrets, or change application policy.
- Provider terms for retention, training use, human review, subprocessors, geographic processing, deletion, incident handling, and legal access must be evaluated before selection.
- Requests must exclude credentials, tokens, session material, unrelated personal information, and unnecessary provenance or identifiers.
- Retained provenance should prefer source identifiers, manifests, hashes, task metadata, and bounded summaries over indefinite copies of prompts, responses, or source text.
- AI responses remain untrusted AI suggestions and cannot overwrite source material, invoke privileged operations, or become Canon automatically.
- Provider failure, timeout, malformed output, or policy rejection must leave authoritative content unchanged.

## External Integration Permissions

Future integrations are out of Version 1 scope but must follow this boundary:

- Each integration addresses a documented workflow and requests the least permission, narrowest resource scope, and shortest useful duration.
- Broad account-wide or workspace-wide access requires explicit justification and may not be used merely for implementation convenience.
- Integration tokens are encrypted or otherwise strongly protected server-side, never exposed to the browser beyond a provider-controlled authorization exchange, and revocable independently.
- Read, write, delete, publish, and administrative permissions are distinct. A read workflow must not receive write or delete authority.
- Synchronization direction, source of truth, conflict behavior, remote deletion, disconnection, expiration, and partial failure must be explicit.
- Imported or synchronized data retains external provenance and does not gain Canon status automatically.
- An integration never receives unrestricted Workspace access and never becomes the sole custodian of the archive.
- Disconnecting or losing an integration must leave the core application, export, backup, and restoration usable.

## Logging and Telemetry Boundaries

Routine operational logs, analytics, traces, metrics, crash reports, alerts, and telemetry must not contain sensitive story content.

Prohibited routine telemetry includes:

- scene text, notes, manuscript excerpts, artwork or object bodies;
- raw search terms where they may contain story content;
- AI prompt or response bodies;
- uploaded or imported document bodies;
- credentials, keys, tokens, cookies, authorization headers, reset links, or MFA material;
- request or response bodies for private operations;
- exports, backups, database dumps, or restoration content; and
- sensitive filenames, titles, full URLs, query strings, stack locals, or identifiers when less-sensitive correlation is sufficient.

Permitted operational data may include timestamps, component and operation names, coarse status or error categories, latency, bounded counts, job state, non-secret correlation identifiers, and carefully designed security events.

Logging should use explicit structured allowlists rather than serializing arbitrary requests, records, exceptions, or objects. Access, retention, deletion, redaction verification, and provider transmission must be documented. Third-party telemetry is an external integration and requires privacy review before use.

## Audit Records Versus Operational Logs

Audit records and operational logs serve different purposes.

Audit records are durable application records needed to explain security-sensitive or authority-changing events. They may include authentication and recovery events, credential or factor changes, session revocation, integration grants and revocations, export and backup operations, restoration, destructive purge, and author-approved state transitions. They use stable record or operation references and must preserve integrity without copying unnecessary creative content.

Operational logs diagnose availability, performance, and errors. They are not authoritative provenance, approval history, or creative state. They may be shorter-lived, sampled, rotated, and deleted without changing domain truth.

Neither store may contain credentials or routine creative bodies. Audit access is restricted and audited. Exact event schemas, retention, timestamp precision, tamper-evidence mechanism, and storage separation remain open decisions.

## Backup and Export Protection

Backups and exports may contain the complete creative archive and must be protected accordingly.

- Creation, listing, download, verification, deletion, and retention changes require authenticated, authorized server-side workflows.
- Artifacts must never be placed at public or indefinitely reusable URLs.
- Temporary download grants, if used, are short-lived, single-purpose, and bound to the authorized artifact.
- Artifacts must exclude credentials, sessions, API tokens, unrelated logs, and secret-bearing configuration.
- Manifests should reveal only what is needed and are themselves sensitive when they expose titles, structure, identifiers, or filenames.
- Integrity and format-version information must detect truncation, substitution, missing objects, and unsupported representations.
- Backup copies should be sufficiently separated from live failure domains and protected from unauthorized deletion or overwrite.
- Encryption, key custody, rotation, retention, secure disposal, offline copies, and owner-held export protection require documented procedures.
- The interface must communicate that downloaded artifacts leave application control and remain private.
- `private-data/`, manuscripts, artwork, databases, database snapshots, exports, and backups must never be committed to Git.

## Restoration Security

Restoration is a privileged data-ingestion and state-replacement workflow. It must not bypass authorization, validation, provenance, or migration rules.

- Only an explicitly authorized and recently authenticated owner or separately authorized recovery operator may initiate restoration.
- A backup is validated for format, version, manifest integrity, authenticity where supported, expected record groups, object references, size limits, and incomplete-operation markers before use.
- Restoration should occur in an isolated or deliberately prepared target and must not overwrite the working archive through an ordinary request.
- Imported backup content remains untrusted until parser, schema, ownership, reference, link, revision, lifecycle, and migration checks pass.
- Migrations are deterministic where practical, preserve identity and meaning, report transformations, and never silently promote authority or discard provenance.
- Restored credentials, sessions, tokens, deployment secrets, and provider access must not become active merely because they appear in an artifact.
- Derived indexes and backlinks are rebuilt or verified from authoritative records.
- Activation requires explicit review of validation results and must retain restoration provenance and audit records.
- Failure must leave the prior authoritative archive intact or provide a tested rollback path.
- A restoration is not successful until representative authenticated application checks confirm usable content, states, links, provenance, lifecycle behavior, and private objects.

## Administrative and Deployment Access

- Administrative access is separate from ordinary owner use and limited to documented operational tasks.
- Deployment, host, database, object-storage, secret, backup, and recovery access use individual or attributable credentials where supported, least privilege, and MFA appropriate to risk.
- Public administrative consoles, debug endpoints, development servers, database ports, job dashboards, and storage consoles are prohibited unless separately protected and explicitly required.
- Production access should be time-bounded or enabled only when needed where practical, and security-sensitive administrative actions should create events.
- Operators must not routinely inspect creative content. Emergency content access requires a documented purpose, minimum necessary scope, and auditability.
- Development and testing must use synthetic or deliberately approved non-sensitive data. Production databases, manuscripts, artwork, exports, or backups must not be copied into routine development environments.
- Deployment must be reproducible, reviewable, and able to roll back application changes without rolling back or corrupting authoritative data.
- Break-glass access, if implemented, requires strong protection, independent recovery, explicit use, and post-use rotation and review.

The final hosting and deployment access model is undecided.

## Dependency and Supply-Chain Risk

- Minimize dependencies and client-side third-party code, especially components that process rich text, documents, archives, authentication, cryptography, uploads, or AI responses.
- Use supported versions from authenticated sources and preserve lockfiles or equivalent reproducibility metadata.
- Review direct dependencies, critical transitive dependencies, maintainership, release practices, licenses, known vulnerabilities, and update cadence before adoption.
- Build and deployment workflows must protect source, artifacts, signing or publishing credentials, and dependency caches from unauthorized modification.
- Automated dependency updates may propose changes but must not deploy without review and proportionate verification.
- Packages, containers, actions, plugins, and build scripts execute code and require the same caution as source changes.
- Remove unused dependencies and features, and define a timely process for security updates.
- Where practical, record a software bill of materials or equivalent dependency inventory for incident response.

No package installation or technology selection is authorized by this document.

## Vulnerability Response

The project must maintain a practical vulnerability-response process that can:

1. receive or discover a report without requiring disclosure of private content;
2. assess affected versions, components, assets, exposure, exploitability, and data impact;
3. contain the issue by disabling a feature, restricting access, rotating credentials, revoking sessions, or isolating a component;
4. remediate through a reviewed change and proportionate regression testing;
5. deploy or communicate the fix through the approved operational process;
6. verify containment and restoration of normal security posture; and
7. document lessons, affected assumptions, and required architecture or decision updates.

Known vulnerabilities affecting exposed or sensitive components require risk-based deadlines. A low-maintenance single-user deployment still requires a way to learn about and apply security updates.

## Security Testing Expectations

Before Version 1 acceptance, testing should cover:

- unauthenticated denial for every private route, API, search, download, object, export, backup, restore, and administrative operation;
- authorization and Workspace scoping using altered identifiers and crafted requests;
- authentication throttling, generic errors, session fixation, expiration, revocation, sign-out, credential changes, and recovery;
- CSRF protections and origin handling for state-changing actions;
- contextual output encoding, rich-content sanitization, and content security policy behavior;
- injection resistance across database, search, templates, headers, paths, files, archives, importers, and job payloads;
- upload and import limits, malicious files, active content, traversal, archive bombs, parser failures, and cleanup;
- SSRF controls, redirects, DNS changes, internal addresses, timeouts, and response limits for any server-side fetch;
- secret scanning and checks that secrets do not appear in client assets, Git, logs, errors, exports, or routine backups;
- private object-storage access, expiration, cache policy, cross-Workspace attempts, orphan handling, and public-access configuration;
- AI context boundaries, prompt-injection resistance, provider failure, credential isolation, and unchanged source content on failure;
- backup confidentiality, integrity verification, artifact authorization, and representative restoration;
- restoration rejection of malformed, incompatible, malicious, incomplete, or authority-altering artifacts;
- dependency and deployment configuration review; and
- verification that routine logs, analytics, traces, and error reports exclude sensitive content.

Use unit, integration, end-to-end, configuration, and adversarial tests in proportion to the control. High-risk parsers and authorization boundaries should receive fuzzing or focused security review where practical. Security regressions must block release when an invariant is violated.

## Incident Response Expectations

An incident-response procedure must identify how to:

- detect and triage suspected unauthorized access, secret exposure, malicious upload, provider disclosure, data corruption, or backup compromise;
- preserve privacy-conscious evidence without copying unnecessary creative content;
- revoke sessions, credentials, tokens, integration grants, and administrative access;
- isolate affected components and disable risky AI, import, export, or integration capabilities;
- determine affected assets, time window, external recipients, and integrity impact;
- recover from a known-good, verified backup without bypassing restoration security;
- communicate clearly to the owner, including uncertainty and any external-provider obligations;
- rotate secrets and verify that old credentials no longer work;
- validate content integrity, provenance, states, and audit history after recovery; and
- perform a post-incident review and update architecture, tests, procedures, and accepted risks.

The response plan must be usable when the application itself, primary credential, or live database is unavailable. Exact notification duties depend on deployment, providers, content, and applicable law and remain to be determined.

## Security Invariants

The following must remain true regardless of technology choices:

- Strange Novelty is private by default.
- Only the authenticated owner may access creative content in Version 1.
- Client-side hiding is not authorization.
- Authentication and authorization are enforced server-side for every private operation.
- Workspace ownership is checked from authoritative data, not accepted from the client.
- Unauthenticated, unauthorized, malformed, or ambiguous requests fail closed.
- Credentials, API keys, tokens, encryption material, and secrets are never exposed to the browser or committed to Git.
- Sensitive story content does not appear in routine logs, analytics, error reports, traces, or telemetry.
- Private objects are not publicly accessible by default.
- The database and administrative interfaces are not directly exposed to browsers.
- External AI requests use narrow, deliberate, task-specific context and clearly cross a trust boundary.
- AI providers and integrations never receive unrestricted Workspace, database, object-storage, filesystem, export, or backup access.
- AI and integration outputs are untrusted and cannot silently overwrite content, change authority, or become Canon.
- File uploads and imported HTML, Markdown, documents, archives, and records are treated as untrusted input.
- Background processes receive bounded service authority and cannot infer author approval.
- `private-data/`, manuscripts, artwork, databases, snapshots, exports, backups, and secret-bearing configuration are never committed.
- Exports and backups remain private content and exclude live credentials and sessions.
- Restoration does not bypass authorization, validation, provenance, concurrency, integrity, or migration rules.
- Recovery and administrative access do not silently change Workspace ownership or creative authority.
- Operational logs are not authoritative audit records.
- Security-sensitive and authority-changing actions are explicit, attributable, and reviewable.
- No external provider is the sole custodian of the archive.
- Loss or compromise of the AI provider or a future integration does not prevent ordinary access to the authoritative archive.
- The old Story Engine remains reference-only and is never modified by Strange Novelty work.

## Explicit Non-Decisions

This document does not select:

- the final authentication provider or authentication protocol;
- whether authentication is locally managed or delegated;
- the password-hashing implementation or parameters;
- the final MFA method or whether MFA is mandatory in every deployment;
- the account-recovery channel or identity-proofing procedure;
- session storage, token format, idle timeout, or absolute timeout;
- the final authorization library or policy framework;
- the hosting provider, cloud vendor, deployment topology, operator, or network exposure;
- the database, database host, object-storage provider, or storage topology;
- the at-rest encryption product, field-level encryption scope, key-management system, or key custodian;
- the secret manager or environment-configuration system;
- the logging, monitoring, alerting, analytics, error-reporting, or audit-storage products;
- the malware scanner, sanitizer, document parser, archive library, or isolation mechanism;
- the AI provider, model, credential method, retention policy, or acceptable processing region;
- any future integration provider or permission set;
- the backup destination, encryption mechanism, format, schedule, retention, or recovery objectives;
- the vulnerability scanner, dependency service, build platform, deployment tool, or security-testing framework; or
- any application language, framework, package, or final security product.

These decisions require review against this architecture, the deployment threat model, operability, privacy, recovery, and applicable provider terms. Significant durable choices should be recorded in architecture decision records before implementation depends on them.

## Open Questions

1. Where will Version 1 run, who will operate it, and will its sign-in endpoint be exposed to the public internet?
2. Which authentication model best balances account-takeover resistance, recovery, portability, and low maintenance for one owner?
3. Is MFA mandatory for owner sign-in, administrative access, or both, and which recovery path avoids a single unrecoverable factor?
4. What idle and absolute session durations fit the writing workflow, and which actions require recent authentication?
5. How will active sessions be displayed, revoked, and invalidated after credential or recovery changes?
6. What account-recovery evidence and emergency procedure are acceptable without creating an operator bypass?
7. Which service principals are required, and what exact database, object-storage, job, export, backup, and restore permissions does each receive?
8. Does Version 1 need private object storage beyond exports and backups, and what direct-transfer model, if any, is acceptable?
9. Which data requires protection beyond platform-level at-rest encryption, and who controls and recovers encryption keys?
10. Where will secrets live, how are they delivered to components, and how often are they rotated and tested?
11. Which browser content format and editor model will be used, and what sanitizer and content security policy support it safely?
12. Does Version 1 support any import or attachment workflow, and which exact formats, sizes, parsers, isolation, and retention rules apply?
13. Will the application fetch any user-supplied URL in Version 1, and if so, what allowlisted purpose and SSRF controls apply?
14. What is the single Version 1 AI task, its maximum context, excluded content, context-preview behavior, and failure mode?
15. Which AI-provider retention, training-use, human-review, subprocessor, geographic, deletion, and incident terms are acceptable?
16. What AI request and response metadata is necessary for provenance without retaining sensitive bodies unnecessarily?
17. Which operational events and security events are required, who may access them, and how long are they retained?
18. Which audit events require tamper evidence, and how are audit records protected separately from operational logs?
19. What backup and export encryption, key custody, destination, retention, deletion, and offline-copy rules are acceptable?
20. What authenticity and integrity mechanism distinguishes a trusted backup from a tampered restoration artifact?
21. What isolated restoration environment and activation process prevent accidental overwrite of the live Workspace?
22. Which representative malicious and corrupted artifacts must restoration testing reject?
23. What recovery point and recovery time objectives match the owner’s tolerance for data loss and downtime?
24. Which administrative access paths are necessary, how are they authenticated, and what break-glass procedure is supportable?
25. What dependency inventory, update cadence, vulnerability severity targets, and release-blocking rules will Version 1 use?
26. How will security advisories and incidents be detected and communicated in a low-maintenance deployment?
27. Which deployment-specific legal, privacy, breach-notification, or data-location obligations apply?
28. Which of these choices require architecture decision records before the first implementation milestone begins?
