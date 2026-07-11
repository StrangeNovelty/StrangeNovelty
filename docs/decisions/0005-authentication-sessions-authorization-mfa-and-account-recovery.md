# ADR-0005: Authentication, Sessions, Authorization, MFA, and Account Recovery

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 authentication, session, authorization, MFA, and account-recovery model, while complete Django models, PostgreSQL schema, package choices, bootstrap mechanism, cookie settings, timeout values, password policy values, WebAuthn/TOTP implementation details, rate limits, notification channels, and emergency-recovery procedure remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; Django, authentication, WebAuthn, application-security, privacy, data, operations, backup, restoration, and recovery perspectives

## Context

Strange Novelty is a private authenticated web application whose complete archive may contain unpublished manuscripts, artwork, research, provenance, AI context, exports, and backups. Version 1 serves one human repository/application owner and initially one private Workspace. Account takeover would expose that archive and could corrupt creative authority, destroy data, create misleading provenance, or abuse external services.

The single-owner scope reduces administration but not security impact. Version 1 has no public sign-up, teams, invitations, role marketplace, public sharing, or multi-tenant administration. The architecture should not make later additional Workspaces impossible.

ADR-0001 establishes a server-mediated private web application: the browser is untrusted, all private operations are authenticated and authorized server-side, and jobs receive bounded authority. ADR-0002 selects Python/CPython and Django, with Django application services as the policy boundary. ADR-0003 selects PostgreSQL as the authoritative relational database and requires explicit Workspace ownership. ADR-0004 establishes stable identifiers, Scene revisions, optimistic concurrency, conflict behavior, and idempotency without treating identifiers or tokens as authority.

These decisions mean that authentication is necessary but insufficient. An authenticated identity still needs current authorization for a particular Workspace and operation. Every private read and write is reauthorized and Workspace-scoped server-side. Stable IDs, URLs, session identifiers, consistency tokens, CSRF tokens, recovery codes, and idempotency keys do not independently grant domain authority.

Jobs, commands, AI operations, exports, backup, migration, and restoration have bounded authority. No provider or browser becomes authoritative for creative state. Secrets remain server-side and outside Git. Production data is excluded from ordinary development and CI.

Account recovery must not be easier to abuse than ordinary authentication. Administrative access must not silently imply creative approval or Canon authority. A database operator may be technically capable of changing data, but that capability is not an ordinary product permission and does not establish author intent.

The decision must distinguish:

- identity proofing from authentication;
- authentication from authorization;
- account ownership from Workspace authorization;
- Django staff or superuser administration from authorial approval;
- session authentication from CSRF protection;
- MFA from recent reauthentication;
- WebAuthn credential identity from Strange Novelty record identity;
- biometric device unlock from biometric data received by the server;
- password reset from MFA recovery;
- account recovery from backup restoration;
- recovery codes from ordinary passwords;
- session revocation from database deletion;
- browser device naming from trusted-device status;
- remember-me convenience from indefinite authentication;
- operational administrator access from ordinary owner access;
- authenticated identity from permission to perform a particular mutation; and
- security events from manuscript-bearing application logs.

Identity proofing establishes who should control an account, using evidence and a bootstrap or recovery procedure. Authentication establishes that a request currently controls an enrolled authenticator. Authorization determines whether that actor may perform the specific requested operation against current authoritative state.

Exact hosting, deployment, secret-management provider, email provider, authentication package, Python and Django versions, PostgreSQL version, password hasher, WebAuthn library, MFA package, and external identity provider remain undecided unless a later accepted decision selects them.

## Decision

If accepted, Version 1 will use the following account-security model.

1. One locally managed owner account uses Django's supported authentication primitives. Public registration is absent, and externally delegated identity is not required.
2. A strong password remains a supported primary authenticator. Django's maintained password hashing and verification framework, supported hashers, password validation, minimum length, and compromised/common-password screening are used.
3. MFA is required before real private content is introduced unless a documented implementation blocker justifies a temporary, bounded exception.
4. WebAuthn security keys or passkeys are the preferred required MFA mechanism if a maintained Django-compatible implementation can be selected, reviewed, and tested.
5. At least two WebAuthn authenticators should be registered before recovery depends exclusively on WebAuthn. Protected one-time recovery codes remain available. TOTP may be a bounded fallback if WebAuthn implementation or device availability cannot meet Version 1 requirements.
6. SMS, voice-call factors, and security questions are excluded. Email alone is not automatically sufficient to disable MFA or seize the account.
7. Django server-side, database-backed sessions use opaque cookies. Sessions are revocable server-side; bearer tokens are not stored in browser-accessible storage.
8. Session cookies are Secure, HttpOnly, SameSite-constrained, narrowly scoped, and contain neither manuscript content nor reusable credentials beyond the opaque session identifier.
9. CSRF protection remains enabled for every cookie-authenticated state-changing request, including JSON and editor requests.
10. Authentication and privilege changes rotate the session identifier. Multiple named and reviewable device sessions are allowed, with owner-visible revocation, bounded idle expiry, and bounded absolute expiry. Unlimited persistent remember-me behavior is prohibited.
11. High-impact operations require recent authentication. Failure or cancellation leaves the operation unapplied.
12. Authorization is explicit in Django application and query services using the current actor, Workspace, record lifecycle, concurrency state, and operation rules.
13. Django staff or superuser status does not automatically grant creative approval or Canon authority. Database roles, Django permissions, route guards, and possible PostgreSQL row-level security are defense in depth, not substitutes for application authorization.
14. Recovery prefers an additional registered WebAuthn authenticator, then protected one-time recovery codes, with bounded TOTP recovery where configured. Recovery triggers review or revocation of sessions, MFA re-enrollment where appropriate, a security event, and owner notification through a later selected channel.
15. Direct database edits and environment-variable bypasses are not ordinary recovery. Any emergency repair path must be separately documented, protected, attributable, audited, and followed by credential and session rotation and explicit owner review.
16. Authentication, recovery, rate-limit, session, and administrative events retain bounded security metadata but never manuscript content or credential material.

## Account and Identity Model

Version 1 has one locally managed human account representing the owner who authenticates to the application. Account identity and Workspace identity are separate records and concepts. The account may be authorized for the initial Workspace without making the account identifier the Workspace identifier or embedding ownership in a username.

Account ownership means control of the enrolled account authenticators and approved recovery paths. Workspace authorization means current permission, derived from authoritative server-side relationships, to access a particular Workspace. An authenticated account is not implicitly authorized for every present or future Workspace.

No public sign-up exists in Version 1. There are no invitations, teams, public identities, externally visible profiles, or general role marketplace. Username, email, and other account identifiers must not reveal story titles, character names, unpublished concepts, or other creative information.

Account disablement denies authentication and ordinary access while preserving the archive according to lifecycle, export, backup, and recovery rules. Disablement is not deletion and does not change creative provenance or Canon.

The system does not claim that local enrollment performs legal, governmental, or real-world identity proofing. It establishes control of the application-owner account through a protected bootstrap. Any future transfer of ownership requires a separately reviewed identity-proofing and authority-transfer process.

## Initial Owner Bootstrap

Initial owner enrollment occurs through a protected bootstrap workflow available only to an authorized operator in an approved deployment context. It creates the first owner account and establishes its initial authenticators without exposing default credentials.

The bootstrap workflow must:

- be unavailable to ordinary unauthenticated web traffic unless a later design proves an equally protected, single-use flow;
- require explicit protected operator action;
- prohibit default, vendor-supplied, shared, or repository-stored credentials;
- verify that no owner has already been enrolled;
- fail closed under ambiguity or partial failure;
- create a bounded security event without credential material;
- require completion of password and recovery enrollment and MFA enforcement before real private content is introduced; and
- disable, invalidate, or permanently exhaust its enrollment capability after successful completion.

Rerunning deployment, restoring application binaries, or knowing a bootstrap URL must not silently recreate or replace the owner. Bootstrap does not confer Canon authority beyond the ordinary owner authorization recorded by the application.

The exact management command, console workflow, deployment mechanism, one-time bootstrap evidence, and operator credential are later decisions.

## Password Authentication

The owner may authenticate with a strong password as the primary factor. Password handling uses Django's maintained password hashing, verification, upgrade, and validation interfaces rather than custom cryptography.

Password rules are:

- plaintext passwords are never stored, logged, placed in analytics, included in exports or backups as plaintext, or returned to a browser after submission;
- password managers and paste are permitted;
- minimum length and compromised/common-password screening are applied with privacy-conscious implementation;
- arbitrary character-class composition rules are avoided because they encourage predictable transformations without reliably increasing entropy;
- arbitrary periodic rotation is avoided unless compromise is suspected, evidence requires it, or a later applicable policy mandates it;
- password change requires a valid current session, current authentication as appropriate, and recent authentication;
- password reset is treated as recovery, invalidates appropriate sessions and recovery state, and does not by itself satisfy MFA recovery; and
- authentication failures use generic responses and rate limiting.

The exact minimum length, maximum accepted length and denial-of-service controls, supported Unicode behavior, compromised-password source, password-reset workflow, password hasher, work factor, and tuning are selected at implementation time from supported Django recommendations and verified against the deployment threat model.

Passwords are not recovery codes. A password is a reusable primary authenticator stored through a slow password verifier. A recovery code is a randomly generated, one-time recovery credential with distinct lifecycle, display, storage, and response behavior.

## MFA Strategy

MFA is required for the owner before real private content is introduced. If a maintained and testable WebAuthn integration cannot be selected in time, a temporary exception must be explicitly documented with scope, compensating controls, owner acceptance, deadline, and removal criteria. Deferring MFA by default is rejected.

Phishing-resistant WebAuthn is preferred. Password plus WebAuthn provides two distinct factors while retaining a broadly understood primary authenticator and a portable local account. WebAuthn may use roaming security keys or appropriately protected platform passkeys.

Before enforcement, the owner must have either multiple registered WebAuthn authenticators or a tested protected recovery path using one-time recovery codes. At least two WebAuthn authenticators should be permitted and encouraged before WebAuthn becomes the sole ordinary recovery dependence.

Authenticator labels are user-provided display metadata. A label such as "office key" or a browser-supplied device description is not proof that a device is trusted, still possessed, or uniquely identified.

MFA removal requires recent authentication and another valid authenticator or recovery path. Enrollment, replacement, removal, and recovery-code regeneration create bounded security events and trigger review or revocation of sessions according to later policy.

SMS, voice call, and knowledge-based security questions are excluded because of interception, reassignment, social-engineering, and memorized-secret weaknesses. Email is not automatically accepted as an MFA-removal factor.

Exact package, WebAuthn attestation policy, resident or discoverable credential policy, authenticator attachment, user-verification requirements, enterprise attestation behavior, and browser-support matrix remain later implementation details.

## WebAuthn Boundary

A WebAuthn credential is an authenticator-scoped public-key credential used to authenticate the account. Its credential identifier is not a Strange Novelty domain-record identifier, Workspace authority, stable URL permission, or creative provenance identity.

The server stores public credential material and bounded metadata required for verification, lifecycle, display, and anomaly detection. It does not receive or store the authenticator's private key.

Platform biometric unlock, when used, occurs locally between the person and authenticator or device. The server receives a signed protocol result and relevant flags; it does not receive fingerprints, facial images, voiceprints, or biometric templates. The application must not describe server-side possession of biometrics where none exists.

WebAuthn registration and authentication must validate the expected relying-party identity, origin, challenge, account binding, ceremony type, credential state, signature, and required user-presence or user-verification properties. Challenges are short-lived, single-purpose, unpredictable, and unusable as domain authorization.

Credential cloning indicators or authenticator counters, where available, inform risk handling but are not assumed universally reliable. Attestation is not required merely to collect device identity; its privacy, compatibility, and operational costs require explicit review.

Passkey synchronization introduces platform-provider and account-recovery dependencies outside Strange Novelty. Those dependencies may be acceptable for convenience, but at least one independent recovery path should prevent a single ecosystem account from becoming the sole custodian of application access.

## TOTP Fallback Boundary

TOTP may be offered as a bounded fallback MFA method when WebAuthn library maturity, supported browsers, owner device availability, or deployment constraints prevent WebAuthn from satisfying Version 1 requirements. It is not preferred over phishing-resistant WebAuthn.

TOTP enrollment requires recent authentication, protected generation and presentation of the seed, verification of a valid code before activation, and protected server-side storage necessary for verification. The seed must not appear in logs, analytics, security events, exports, source control, or ordinary session state.

TOTP codes are phishable and shareable, and synchronized authenticator applications may depend on an external account. Rate limiting, replay resistance within the accepted window, clock handling, bounded drift, and secure seed storage are required.

TOTP recovery does not mean retrieving or displaying the existing seed. Loss of the TOTP device uses another enrolled WebAuthn authenticator, a one-time recovery code, or the separately documented emergency procedure. Exact algorithm, code length, time step, drift window, issuer label, QR representation, and package remain implementation decisions consistent with current standards and maintained support.

## Session Model

Version 1 uses Django server-side, database-backed sessions with opaque session identifiers carried in cookies. The authoritative session state is revocable server-side and stored in PostgreSQL through Django's supported session framework or an equivalently reviewed server-side implementation.

Database-backed sessions are preferred initially because they provide understandable persistence, review, revocation, and transactional operability without making a cache mandatory. Cached sessions may later be used as an optimization only if loss, eviction, fallback, consistency, revocation, and outage behavior are explicitly designed.

Signed-cookie sessions are not selected because server-side invalidation and bounded security-state review are core requirements, while signed cookies retain readable client-held state and complicate immediate revocation. Stateless bearer JWTs in browser-accessible storage are rejected because theft enables replay, revocation is harder, JavaScript exposure increases risk, and Version 1 has no independent API-client need that justifies them.

Short-lived access tokens plus refresh tokens are also not selected for the browser application. They add token rotation, storage, replay, revocation, and synchronization complexity without improving the server-rendered or same-origin Django trust model.

Multiple concurrent device sessions are permitted. Each is independently identifiable to the owner using bounded display metadata and independently revocable. A displayed name is for review convenience and is not trusted-device status.

Persistent remember-me behavior, if later offered, may extend a bounded session policy but never creates indefinite authentication, bypasses absolute expiry, or satisfies recent authentication for high-impact operations.

## Session Cookie Policy

The session cookie must be:

- Secure in every production-like deployment;
- HttpOnly so ordinary JavaScript cannot read it;
- constrained by an appropriate SameSite policy consistent with the supported login and integration flows;
- narrowly scoped by host and path;
- opaque and free of manuscript content, passwords, MFA secrets, recovery codes, provider tokens, account profile data, or reusable domain credentials; and
- transmitted only over protected transport.

Session credentials are not stored in localStorage, sessionStorage, IndexedDB, browser-managed application databases, JavaScript variables intended for persistence, or URLs. Full cookies and session identifiers are excluded from logs, traces, analytics, errors, provenance, and security events.

Cookie prefixes, cookie names, domain attributes, path values, SameSite value, and transport-security configuration depend on the final deployment and remain later configuration decisions. Development exceptions must never silently weaken production settings.

## Session Lifecycle and Revocation

Successful authentication rotates the session key to prevent fixation. Privilege or credential changes that could preserve an attacker's session also rotate or replace the session as appropriate.

Logout revokes the current server-side session. Closing a browser is not treated as reliable revocation. Password reset, suspected compromise, account disablement, recovery-code use, emergency recovery, or explicit owner action can revoke all sessions. Password or MFA changes revoke or review sessions according to a documented policy that favors containment.

Each session records only bounded review metadata, such as:

- creation and last-use times;
- authentication and recent-authentication times or assurance markers;
- coarse client or device description;
- coarse network metadata where justified;
- revocation state and reason category; and
- bounded security-event references.

Session records do not store manuscript content, passwords, WebAuthn private keys, TOTP seeds, recovery-code plaintext, provider tokens, raw authorization headers, full cookies, or arbitrary request bodies.

Idle and absolute expirations are both required. Exact durations are decided later through a documented policy balancing long writing sessions with unattended-device and stolen-session risk. Expired or revoked sessions fail closed, cannot resume a partially authorized privileged operation, and require new authentication.

Background jobs never reuse browser sessions. They use separately authenticated service identity and bounded operation authority, revalidate current state before effects, and retain attribution to the initiating owner operation where applicable.

Session revocation deletes or disables an authentication grant. It does not delete the account, Workspace, manuscript, provenance, or database. Database retention and cleanup of expired session rows is an operational lifecycle distinct from user data deletion.

## Recent Authentication

MFA establishes authentication assurance for a login. Recent authentication establishes that the owner has freshly demonstrated control of required factor or factors near a sensitive action. An old MFA-authenticated session does not satisfy recent authentication indefinitely.

Recent authentication is required for at least:

- password change or reset completion;
- WebAuthn or TOTP enrollment, removal, or replacement;
- recovery-code regeneration;
- email, username, recovery-channel, or other credential changes;
- complete archive export;
- destructive purge or equivalent irreversible lifecycle action;
- backup restoration activation;
- session-wide revocation decisions where compromise handling requires confirmation;
- administrative or emergency-access changes; and
- other operations later classified as high impact.

Recent authentication may require the primary password, a phishing-resistant factor, or both depending on the operation and recovery state. Possession of an old session alone is insufficient. A CSRF token, session identifier, recovery code presented in a different context, signed URL, or confirmation button does not substitute.

The recent-authentication window, assurance level, factor combinations, retry behavior, and continuity across tabs remain later policy details. Failure, timeout, or cancellation leaves the requested operation unapplied and does not leave a reusable partial authorization.

## CSRF Boundary

Session authentication and CSRF protection solve different problems. A session cookie identifies an authenticated browser session; CSRF protection prevents another origin from inducing that browser to perform an unwanted state-changing request with ambient cookies.

Django CSRF protection remains enabled for all cookie-authenticated state-changing requests, including form submissions, JSON endpoints, editor saves, AI operations, exports, recovery actions, and administrative requests. JSON content type, fetch APIs, SameSite cookies, custom headers, or route secrecy are not accepted as sole CSRF defenses.

CSRF tokens are request-integrity mechanisms, not authentication credentials or domain authority. Possession of a token does not authorize a Workspace mutation. Each request still authenticates the session and rechecks authorization, lifecycle, input, concurrency, and operation rules.

Allowed origins, trusted origins, proxy headers, HTTPS termination, cross-origin integration flows, and API-specific authentication remain deployment or later interface decisions. Unsafe methods fail closed on missing or invalid CSRF evidence.

## Authorization Model

Every application and query service receives or resolves an authenticated actor and Workspace. It authorizes the requested operation against current authoritative data before returning private information or performing effects.

Authorization checks include, as applicable:

- active account and session state;
- current owner-to-Workspace relationship;
- target record membership in the authorized Workspace;
- record lifecycle, deletion, archive, and restoration state;
- operation-specific permission;
- current revision and optimistic-concurrency token;
- explicit author approval for authority-changing actions;
- provenance and content-state transition rules;
- rate, size, and resource limits; and
- current job, export, backup, migration, restoration, or integration grant.

Every private query is Workspace-scoped from authoritative server data. Every mutation rechecks ownership, lifecycle, concurrency, and operation permission inside the appropriate service and transaction boundary. IDs supplied by a browser are locators only.

Unauthorized responses avoid confirming whether a private account, Workspace, record, revision, export, backup, session, authenticator, or recovery path exists. Generic behavior must still permit the owner to diagnose authorized failures safely.

Browser route guards and hidden controls are usability features only. They may reduce accidental navigation but do not authorize requests.

## Workspace Scoping

The initial owner may have access to one Workspace, but queries do not assume that all rows globally belong to that owner. Workspace scope is explicit in authoritative relationships and enforced for every private record and operation.

Services derive or validate Workspace scope from the authenticated actor and server-side records, not from a hidden field, URL parameter, cookie, stable ID, signed link, browser cache, or previous request. Cross-Workspace identifiers fail without revealing existence.

Direct ownership fields on Workspace-scoped records and PostgreSQL constraints support integrity and efficient scoping. They do not replace service authorization. The model permits later additional Workspaces by adding explicit grants or ownership relationships through a future ADR rather than rewriting global-superuser assumptions.

Search, backlinks, history, AI context, imports, exports, backup, restoration, jobs, and administrative views use the same Workspace boundary. Derived indexes and caches cannot broaden it.

## Administrative and Service Authority

Django staff and superuser flags govern framework administration capabilities where used. They do not mean the account has reviewed creative content or may silently mark content Canon, accept an AI suggestion, approve imported material, resolve a conflict, or attribute an action to the author.

A single global superuser check is rejected as the domain authorization model. Operational administrator access is separate from ordinary owner use, least-privileged, attributable, and limited to documented purposes. Routine operation should not require inspecting creative bodies.

Jobs, commands, AI gateways, export workers, backup processes, migration tools, restoration tools, and integration adapters use separate service identity or execution context with bounded operation authority. They cannot reuse browser sessions, infer author approval, expand their Workspace scope, or promote content authority.

Emergency administrative mutation is exceptional. It requires a documented purpose, minimum necessary scope, protected operator access, security-event and evidence handling, preservation of application invariants, and owner reconciliation. Technical capability is not creative authorization.

Django model permissions and groups may support administrative organization or future roles. Database roles restrict component access. PostgreSQL row-level security may later add defense in depth if its migration, job, backup, restoration, and operator implications are understood. None replaces explicit Django application-service authorization.

## Account Recovery

Ordinary recovery restores access to the existing owner account without granting broader Workspace or creative authority. It must resist account enumeration, guessing, phishing, replay, support impersonation, and factor-removal abuse.

Preferred recovery order is:

1. use another registered WebAuthn authenticator;
2. use a pre-generated one-time recovery code through a protected recovery flow;
3. use a bounded TOTP path where TOTP remains enrolled and policy permits it; and
4. invoke a separately documented emergency recovery procedure when ordinary authenticators are unavailable.

Verified email may deliver notifications or participate as one item of evidence in a later reviewed procedure. Email alone does not automatically reset the password, remove MFA, replace authenticators, or seize the account. Exact notification channels and email provider remain undecided.

Password reset and MFA recovery are distinct. Resetting a forgotten password does not prove possession of an enrolled second factor. Recovering MFA does not silently select a new password. A combined emergency workflow must meet the strongest relevant controls and be explicit about each state change.

Recovery responses are generic and do not disclose whether an account, email, authenticator, recovery code, or session exists. Attempts are rate-limited and produce bounded events without secrets.

Successful recovery revokes or reviews other sessions, invalidates used or superseded recovery state, requires MFA re-enrollment where appropriate, notifies the owner through later approved channels, and records a security event. It never changes Canon, accepts content, or attributes creative approval.

Backup restoration is not account recovery: a backup proves possession of an artifact, not the identity or current authority of a person. Restored credentials, sessions, and tokens do not become active merely because they appear in an archive.

## Recovery Codes

Recovery codes are generated during MFA enrollment or explicit regeneration. They are high-entropy, random, one-time credentials intended for offline owner custody.

Recovery-code requirements are:

- shown once through a protected authenticated flow;
- never subsequently retrievable as plaintext;
- stored server-side only as verifier hashes with bounded metadata;
- excluded from logs, telemetry, session records, exports, backups where live credential recovery would be unsafe, and source control;
- compared using a safe verifier path;
- individually invalidated after successful use;
- collectively invalidated and replaced on regeneration;
- protected by rate limiting and generic errors; and
- distinguished from reusable passwords in user guidance and implementation.

The owner is instructed to keep codes offline and separate from the primary device and password manager account where practical. The application cannot verify the safety of a saved copy and must not label a browser or storage location as trusted merely because it was used during enrollment.

Use of a recovery code triggers session review or revocation, MFA re-enrollment where appropriate, owner notification through a later selected channel, and a bounded security event. Exact code count, format, entropy, verifier, display layout, and retention policy remain implementation decisions.

## Emergency Recovery

No ordinary environment flag, support toggle, hidden URL, database edit, shared secret, or deployment restart may disable MFA or establish owner access.

A separately documented emergency procedure may exist because no-recovery designs can permanently lock the owner out. It is a break-glass operational process, not a routine application feature. It must require:

- protected, attributable operator access independent of public application traffic;
- explicit evidence that ordinary recovery paths are unavailable;
- preservation of privacy-conscious evidence and existing security events;
- minimum necessary changes;
- no silent reassignment of Workspace or creative authority;
- credential rotation and MFA re-enrollment;
- revocation of active sessions and superseded recovery material;
- owner notification and explicit post-recovery review;
- reconciliation through application invariants; and
- post-use rotation or closure of emergency access.

Direct database edits are emergency repair mechanisms only if the procedure separately documents constraints, transaction safety, audit reconstruction, backup, validation, and rollback. Such edits do not count as successful ordinary recovery and cannot create evidence of authorial approval.

Disabling MFA through an environment variable or support action is rejected as an ordinary mechanism. If a one-time deployment-controlled repair tool is later approved, it must be fail-closed, single-purpose, unavailable during normal operation, and covered by the same emergency requirements.

No exact operator, deployment path, offline secret format, quorum, notification channel, or identity-proofing evidence is selected here.

## Authentication and Security Events

The application records bounded events needed to review authentication and recovery without copying creative content. Event categories include:

- bootstrap attempted, completed, rejected, or invalidated;
- login success and failure categories;
- logout, expiry, session creation, rotation, and revocation;
- password change, reset, and verifier upgrade;
- WebAuthn or TOTP enrollment, use, removal, and replacement;
- recovery-code generation, regeneration, and use without plaintext;
- recovery initiation, completion, failure category, and emergency use;
- rate-limit activation and suspicious authentication patterns;
- account disablement and re-enablement;
- recent-authentication success or failure category; and
- administrative or service-authority use affecting account security.

Events use timestamps, actor or account references where disclosure is authorized, coarse outcome and reason categories, session or authenticator references where necessary, and privacy-bounded network/client metadata. They never contain passwords, WebAuthn private keys, biometric data, TOTP seeds, recovery-code plaintext, full cookies, session secrets, authorization headers, full reset links, manuscript bodies, prompts, responses, exports, or backups.

Security events are not creative provenance, revision history, Canon approval, or general manuscript-bearing application logs. Access, retention, integrity, alerting, and export rules are later decisions. Operational logs remain separately bounded and may be shorter-lived.

## Rate Limiting and Enumeration Resistance

Login, password reset, MFA ceremonies, recovery, bootstrap exposure if any, session-management, and recent-authentication endpoints use server-side rate limiting proportionate to account, client, network, and system-level abuse.

Controls must address distributed guessing, denial of service against the sole owner, replay, username enumeration, authenticator probing, recovery-code guessing, and resource exhaustion. Rate limiting does not replace strong authenticators, CSRF, authorization, or anomaly review.

Unauthenticated and unauthorized responses use generic wording and sufficiently consistent status, shape, and timing where practical so they do not confirm account, email, Workspace, record, factor, or recovery state. The authenticated owner may receive more useful information only after authorization.

IP addresses and user-agent strings are sensitive operational metadata. Collection is minimized, coarse where possible, access-controlled, and subject to bounded retention. They are signals, not identity proof, authorization, or trusted-device evidence.

Exact thresholds, windows, keys, backoff, challenge behavior, storage, alerting, and denial-of-service exceptions remain later policy and implementation decisions. Failure must not fall back to unlimited authentication attempts.

## Secrets and Sensitive Data

Passwords, password-reset credentials, WebAuthn challenges, TOTP seeds, recovery codes, session identifiers, signing keys, encryption keys, provider tokens, deployment credentials, and emergency-recovery material are secrets or sensitive authentication data according to their function.

Secrets remain server-side, outside Git, outside client-visible configuration, and outside routine logs, analytics, traces, errors, exports, backups, provenance, and security-event bodies unless a separately reviewed backup requirement securely protects necessary verifier state. Secret-bearing configuration is injected through a later selected deployment mechanism.

The browser receives only the minimum ceremony data required for authentication and never receives server secrets, password verifiers, stored TOTP seeds after enrollment, recovery-code verifier hashes, other sessions' identifiers, WebAuthn private keys, or provider credentials.

Production databases, credentials, manuscripts, exports, and backups are excluded from ordinary development and CI. Tests use synthetic accounts and synthetic content. Secret scanning, safe error handling, explicit log allowlists, protected transport, dependency review, rotation, and incident response are required before production use.

Exact secret manager, encryption product, key custodian, rotation interval, and field-level encryption scope remain undecided.

## Django and PostgreSQL Boundary

Django owns authentication orchestration, session handling, CSRF enforcement, password verification, recent-authentication policy, account lifecycle, authorization, Workspace scoping, recovery workflows, and security-event creation through reviewed services and middleware boundaries.

PostgreSQL is the authoritative relational store for accounts or framework-compatible account references, Workspace grants, server-side sessions, authenticator public data and protected verifier state, recovery-code verifier state, security events, and revocation state where the later schema places them.

Database constraints, uniqueness, foreign keys, transactions, and component roles reinforce integrity. They cannot decide whether a creative operation represents owner approval. PostgreSQL row-level security may provide defense in depth but is not selected here and cannot be the only authorization layer.

Django's built-in authentication primitives are the baseline, not an instruction to expose a default admin interface publicly or to equate framework permissions with domain policy. Any third-party WebAuthn, TOTP, rate-limit, or recovery package requires maintenance, security, privacy, dependency, migration, and portability review.

Complete Django models, PostgreSQL schema, migrations, middleware order, routes, forms, templates, APIs, administrative interfaces, and package choices remain undecided.

## Rationale

The selected direction combines a maintainable local account with strong resistance to phishing, credential stuffing, session theft, recovery abuse, and authorization mistakes.

Password plus WebAuthn avoids making an external identity provider or passkey ecosystem the sole gate to the archive while adding a phishing-resistant factor. Multiple authenticators and hashed one-time recovery codes reduce single-device lockout without turning email or operator convenience into an easy bypass. TOTP provides a deployable fallback but remains secondary because it is phishable.

Database-backed Django sessions fit a private same-origin web application. They keep reusable bearer credentials out of JavaScript-accessible storage and allow immediate review and revocation. Multiple bounded sessions support realistic writing across devices without indefinite remember-me authentication.

Explicit application-service authorization matches ADR-0001 and ADR-0002, keeps domain meaning close to mutations, and allows future Workspaces without pretending that framework superuser status or an opaque identifier expresses author intent.

Recovery is treated as a high-risk authentication state change rather than customer-support convenience. Its containment actions reduce the value of a stolen recovery code and make unusual access reviewable.

## Decision Criteria

Options are evaluated against:

1. resistance to phishing, credential stuffing, replay, session theft, and account takeover;
2. recovery safety without unacceptable permanent lockout risk;
3. explicit server-side Workspace and operation authorization;
4. separation of operational administration from creative authority;
5. compatibility with Django and PostgreSQL without custom cryptography;
6. maintainability by one owner;
7. portability without mandatory external identity dependence;
8. revocation, incident response, and security-event visibility;
9. privacy of manuscript and authentication data;
10. compatibility with exports, backups, migration, and restoration without activating credentials improperly;
11. future ability to add Workspaces without implementing Version 1 team administration; and
12. bounded implementation and dependency risk.

## Alternatives Considered

### Django-local account with password authentication

This is simple, portable, and well supported by Django. Alone, it remains vulnerable to phishing, credential reuse, keylogging, and password-database compromise. It is retained as the primary factor but rejected as the complete model.

### Django-local account with password plus required MFA

Selected as the overall authentication approach. It preserves local control and supported password recovery boundaries while materially improving account-takeover resistance. Its costs are MFA implementation, device enrollment, recovery design, and ongoing dependency maintenance.

### WebAuthn or passkey-first passwordless authentication

This offers strong phishing resistance and good user experience on supported devices. It is not selected as the only Version 1 primary method because device/ecosystem recovery, Django package maturity, bootstrap, cross-device support, and owner lockout need more evidence. It remains a possible future simplification after operational experience.

### Password plus WebAuthn as preferred second factor

Selected when a maintained compatible implementation passes review and testing. It provides phishing resistance without making passkey-provider recovery the sole account-recovery system.

### Password plus TOTP as preferred second factor

TOTP is widely interoperable and easier to implement, but it is phishable and seeds can be copied or exposed. It is accepted only as a bounded fallback, not the preferred factor.

### Email magic-link authentication

Magic links remove memorized-password burden but transfer primary authentication and much recovery risk to the email account, link delivery, URL handling, and email provider. Email compromise could become archive compromise. Not selected as primary authentication.

### Delegated OpenID Connect or OAuth identity provider

Delegation can provide mature MFA and account-risk controls, but introduces provider availability, policy, privacy, identifier mapping, recovery, lockout, and portability dependencies. Version 1 does not require it. A later deployment may add delegated identity through a separate decision without making the provider authoritative for creative state.

### Mutual TLS or VPN-only primary authentication

Network and client-certificate controls can reduce exposure and strengthen administration. They are operational defense in depth, not sufficient primary human authentication: certificate/device lifecycle, sharing, recovery, browser support, and creative-authority mapping remain. Not selected as the application login model.

### One long-lived shared secret

Rejected. It lacks per-session revocation, safe rotation, attribution, phishing resistance, recent authentication, bounded recovery, and separation between people and services.

### Defer MFA until after Version 1

Rejected because real private content makes account takeover archive-wide. A documented temporary bounded implementation exception is possible, but indefinite deferral is not the default architecture.

### Django server-side database-backed sessions

Selected. They provide opaque cookies, server-side revocation, reviewable session state, and low additional operational complexity with the authoritative database.

### Cached sessions

Potential future optimization. Cache loss, eviction, invalidation, fallback, and outage behavior complicate security and operability. Not required for the single-owner workload.

### Signed-cookie sessions

Rejected for Version 1 because immediate server-side revocation and session review are primary requirements. Cookie signing protects integrity, not confidentiality or instant invalidation.

### Stateless bearer tokens or JWTs in browser-accessible storage

Rejected. JavaScript exposure, replay, token leakage, revocation complexity, refresh handling, and no demonstrated independent client need outweigh benefits.

### Short-lived access tokens plus refresh tokens

Rejected for the same-origin browser application. They reduce access-token lifetime but add another high-value credential and complex rotation, reuse detection, revocation, and storage requirements.

### Session cookies with server-side revocation

Selected. This combines browser cookie protections with immediate server control.

### Single session only

Not selected. It simplifies incident response but disrupts legitimate laptop/desktop use and encourages unsafe workarounds. Independent reviewable sessions provide bounded multi-device support.

### Multiple-device sessions

Selected with owner-visible review, independent revocation, idle expiry, absolute expiry, and recent authentication. Device labels do not create trusted-device status.

### Persistent remember me

Unlimited persistence is rejected. A later bounded convenience policy may extend normal sessions without bypassing absolute expiry or sensitive-action reauthentication.

### Explicit application-service authorization

Selected as the primary domain authorization model. It can combine actor, Workspace, lifecycle, concurrency, provenance, and operation rules at the authoritative policy boundary.

### Django model permissions

Useful for framework administration and possible future coarse permissions, but insufficient for record-level Workspace scope, lifecycle, concurrency, and authorial approval. Defense in depth only.

### Django groups and roles

Unnecessary for the Version 1 single-owner product and insufficient by themselves. They may support future multi-user policy through a later ADR.

### PostgreSQL row-level security

Potential defense in depth against query mistakes, but it adds connection-context, migration, administration, job, backup, and restoration complexity. Deferred, and never a substitute for application authorization.

### Browser-side route guards

Retained for usability only and rejected as security enforcement because the browser is untrusted.

### Object-capability or signed-link access

Useful for tightly bounded temporary artifact download in a later decision, but rejected as the general private-domain authorization model. Links can leak, be replayed, and cannot express all current-state rules.

### One global superuser check

Rejected. It conflates framework administration, Workspace access, operational power, and creative approval and prevents safe future Workspace expansion.

### Direct ownership on Workspace-scoped records

Selected as an integrity and query-scoping foundation where appropriate, combined with application-service authorization. A foreign key alone does not authorize an actor.

### Layered defense in depth

Selected: application authorization is primary, reinforced by Django authentication/CSRF, query scoping, database constraints and roles, optional framework permissions, possible later row-level security, protected network/deployment access, security events, and testing.

### Pre-generated one-time recovery codes

Selected as an ordinary recovery path. They are offline-capable and provider-independent but create theft, storage, loss, and user-handling risks mitigated by one-time use, hashing, rate limits, and containment.

### Additional registered WebAuthn authenticators

Selected as the preferred recovery path because they retain phishing resistance and avoid factor downgrade. Cost and physical loss remain concerns.

### TOTP recovery

Accepted only when TOTP is already enrolled and policy permits it. It is not an independent recovery path if the lost device holds the only TOTP seed.

### Verified email recovery

Not selected as sufficient by itself. It may support notification or contribute evidence later, but email compromise and provider recovery must not automatically defeat MFA.

### Administrator-assisted recovery

Rejected as an ordinary workflow for a one-owner application. A separately documented emergency operator process may exist with stronger controls, evidence, rotation, revocation, and review.

### Offline recovery secret

Recovery codes are the selected bounded form. A separate master secret risks becoming an unrotated shared bypass and is not selected without a later design.

### Backup restoration as account recovery

Rejected. Artifact possession does not authenticate a person, and restoration must not reactivate credentials or sessions.

### Direct database edits

Rejected as ordinary recovery. They may be used only as separately documented emergency repair with protected access, invariant reconciliation, audit, rotation, and review.

### Disable MFA through support or environment flags

Rejected as an ordinary mechanism because it creates a high-value bypass. Any emergency tool requires separate approval and break-glass controls.

### No recovery path

Rejected. It minimizes recovery abuse surface but creates unacceptable permanent archive lockout from lost authenticators. Multiple strong, bounded recovery paths better balance takeover and availability risk.

## Comparative Assessment

### Authentication comparison

| Approach | Takeover resistance | Recovery independence | Maintenance | Decision |
| --- | --- | --- | --- | --- |
| Local password only | Moderate | Strongly local | Low | Insufficient alone |
| Local password + WebAuthn | Strong, phishing-resistant MFA | Strong with multiple authenticators/codes | Moderate | Preferred |
| Local password + TOTP | Stronger than password alone; phishable | Good with protected codes | Moderate | Fallback |
| WebAuthn/passwordless | Strong | Ecosystem/device-sensitive | Moderate/high | Deferred as sole primary |
| Email magic link | Depends heavily on email | Email-dependent | Moderate | Not selected |
| Delegated OIDC/OAuth | Provider-dependent; potentially strong | Provider-dependent | Moderate | Deferred |
| mTLS/VPN primary | Strong network/device gate | Operationally difficult | High | Defense in depth only |
| Shared secret | Weak | Poor | Superficially low | Rejected |
| Password without V1 MFA | Moderate | Local | Low | Rejected default |

### Session comparison

| Approach | Server revocation | Browser exposure | Operational complexity | Decision |
| --- | --- | --- | --- | --- |
| Database-backed Django session | Direct | Opaque HttpOnly cookie | Low/moderate | Selected |
| Cached session | Direct if designed correctly | Opaque cookie | Moderate | Deferred optimization |
| Signed-cookie session | Difficult before expiry | Full signed state client-held | Low | Rejected |
| Browser-stored bearer/JWT | Complex | JavaScript-accessible if so stored | Moderate/high | Rejected |
| Access + refresh tokens | Possible but complex | Refresh-token risk | High | Not selected |
| One active session | Direct | Opaque cookie | Low | Not selected |
| Multiple bounded sessions | Direct and independent | Opaque cookies | Moderate | Selected |
| Unlimited remember me | Delayed containment | Long-lived credential | Low UX friction | Rejected |

### Authorization comparison

| Approach | Domain context | Workspace safety | Creative-authority separation | Decision |
| --- | --- | --- | --- | --- |
| Application/query services | Strong | Explicit | Strong | Primary |
| Django model permissions | Coarse | Incomplete alone | Incomplete | Supporting only |
| Groups/roles | Coarse | Future-useful | Incomplete | Deferred |
| PostgreSQL RLS | Row-focused | Strong if correct | Cannot express all intent | Possible defense |
| Browser route guards | Untrusted | Weak | Weak | Usability only |
| Signed links/capabilities | Narrow bearer authority | Leak/replay-sensitive | Weak for mutations | Special-purpose only |
| Global superuser | Weak | Global | Conflates authority | Rejected |
| Ownership fields only | Record relationship | Useful | Incomplete | Integrity support |
| Layered controls | Strong | Strong | Strong | Selected |

### Recovery comparison

| Approach | Takeover resistance | Lockout resistance | Provider dependence | Decision |
| --- | --- | --- | --- | --- |
| Additional WebAuthn authenticator | Strong | Strong if separately held | Device/ecosystem varies | Preferred |
| One-time recovery codes | Strong if protected | Strong | None | Selected |
| Existing TOTP | Phishable | Moderate | Authenticator varies | Bounded fallback |
| Email alone | Email-account dependent | Strong convenience | High | Insufficient alone |
| Administrator assistance | Operator dependent | Strong | Deployment/operator | Emergency only |
| Offline master secret | Theft/storage risk | Strong | None | Recovery codes preferred |
| Backup restoration | Does not prove identity | Misleading | Storage-dependent | Rejected |
| Direct DB edit | Bypasses policy | Strong technically | Operator-dependent | Emergency repair only |
| MFA-disable flag | High bypass risk | Strong technically | Deployment-dependent | Rejected ordinary path |
| No recovery | Strong against recovery abuse | Unacceptable lockout | None | Rejected |

## Evidence

### Repository evidence

- Product vision and principles make privacy, authorial authority, provenance, portability, backup, restoration, and explicit AI boundaries core properties.
- Version 1 scope requires one authorized user to sign in and sign out and denies unauthenticated access to all private creative content.
- The roadmap places secure single-user authentication in the first private writing workspace and requires security and recovery foundations before broader features.
- The architecture overview keeps the browser outside the trusted application and data boundary.
- The data model uses explicit Workspace ownership and distinguishes account, creative authority, lifecycle, provenance, and stable record identity.
- The security architecture requires server-side authentication and authorization, conservative session handling, MFA and recovery review, CSRF, secret isolation, bounded logs, protected backup/restoration, and least-privileged administration.
- The AI-context and integration architectures deny providers direct Workspace authority and require authenticated, Workspace-scoped application operations.
- ADR-0001 through ADR-0004 establish the server policy boundary, Django, PostgreSQL, stable IDs, concurrency, bounded jobs, and non-authoritative client tokens.
- The old Story Engine audit identifies a local desktop trust model with browser-side database and secret access and recommends rebuilding around server-side authorization and separated credentials rather than copying that design.

### Official guidance reviewed conceptually

The decision is informed conceptually by current official and standards guidance without binding to a particular release or package:

- [Django authentication documentation](https://docs.djangoproject.com/en/stable/topics/auth/)
- [Django password management](https://docs.djangoproject.com/en/stable/topics/auth/passwords/)
- [Django sessions](https://docs.djangoproject.com/en/stable/topics/http/sessions/)
- [Django CSRF protection](https://docs.djangoproject.com/en/stable/ref/csrf/)
- [Django security documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-4/)
- [W3C Web Authentication specification](https://www.w3.org/TR/webauthn-3/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP Multifactor Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

Current guidance supports long passwords, compromised-password screening, password-manager use, avoidance of arbitrary composition and periodic-rotation rules, phishing-resistant authenticators, protected recovery, session rotation and revocation, CSRF defenses for cookie authentication, generic authentication errors, rate limiting, and server-side authorization.

### Evidence still required

Before acceptance or implementation:

- confirm the deployment exposure and administrative access model;
- review maintained Django-compatible WebAuthn implementations and their support/security history;
- verify supported browser, platform passkey, and roaming-key behavior;
- perform a synthetic enrollment, second-authenticator, loss, recovery-code, and re-enrollment exercise;
- decide whether TOTP is necessary and review protected seed storage;
- define session metadata, revocation, cleanup, idle expiry, and absolute expiry policy;
- define the recent-authentication assurance matrix for high-impact operations;
- define password validation and supported-hasher configuration from the selected Django release;
- threat-model bootstrap and emergency recovery in the selected deployment;
- define rate-limit and enumeration-resistance behavior under owner lockout and distributed attack;
- verify CSRF behavior for every form, JSON, editor, AI, export, and recovery mutation;
- design application-service authorization tests across altered IDs and future Workspace boundaries;
- define security-event schema, retention, access, integrity, and owner notification;
- verify that export, backup, and restoration exclude or safely invalidate live authentication state; and
- conduct dependency, privacy, accessibility, recovery, and incident-response review.

## Consequences

### Positive

- Phishing-resistant MFA materially reduces password-only account takeover.
- Local account control avoids mandatory identity-provider availability and policy dependence.
- Multiple authenticators and hashed recovery codes reduce permanent lockout without relying on email alone.
- Server-side sessions support immediate review, containment, and revocation.
- Secure HttpOnly cookies keep the session credential out of ordinary JavaScript storage.
- Recent authentication limits damage from an old or unattended session.
- Explicit Workspace-scoped services make authorization reviewable and compatible with later Workspaces.
- Administrative power remains distinct from authorial approval and Canon authority.
- Bounded security events support incident investigation without copying manuscripts.
- Recovery, backup restoration, and operational repair remain meaningfully separate.

### Negative

- WebAuthn integration and recovery ceremonies add dependency and testing complexity.
- The owner must acquire, register, label, safeguard, and periodically test multiple recovery paths.
- Local authentication makes the deployment responsible for password, session, MFA, rate-limit, and recovery security updates.
- Database-backed sessions add persistent state, cleanup, review UI, and revocation workflows.
- Recent-authentication prompts add friction to exports, credential changes, restoration, and destructive actions.
- TOTP fallback weakens phishing resistance and introduces sensitive shared-secret storage.
- Recovery codes can be lost, copied, photographed, or stored beside the primary credentials.
- Generic errors and rate limiting can make legitimate owner troubleshooting harder.
- Emergency recovery remains a powerful operational path that is difficult for one owner to segregate fully.
- Application authorization must be applied consistently to every query, job, command, and derived view.

### Neutral or Operational

- Exact password, cookie, session, rate, and recent-authentication values remain deployment policy.
- Email may be useful for notification without becoming sufficient recovery proof.
- Passkey synchronization may improve usability but adds an external ecosystem dependency.
- PostgreSQL stores authoritative authentication state but does not determine creative intent.
- MFA enrollment does not make a browser or device permanently trusted.
- Backup and restoration still require independent protection and do not solve account recovery.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Password is phished or reused | Archive access attempt | Required phishing-resistant MFA, compromised-password screening, rate limits, events | MFA fatigue or fallback phishing remains possible |
| WebAuthn package is immature or abandoned | Authentication failure or vulnerability | Maintenance/security review, standards tests, bounded dependency, TOTP exception/fallback | Ecosystem changes can require migration |
| All authenticators are lost | Permanent lockout | Multiple authenticators, offline one-time codes, tested emergency procedure | Correlated loss can defeat all ordinary paths |
| Recovery code is stolen | Account takeover | Hash storage, one-time use, rate limits, containment, notification, offline guidance | Plaintext owner copy can be compromised |
| Email account is compromised | Recovery abuse | Email alone cannot remove MFA or seize account | Notifications may be suppressed or observed |
| TOTP is phished or seed copied | Second-factor compromise | Prefer WebAuthn, protect seed, rate/replay controls, bounded use | TOTP remains phishable by design |
| Session cookie is stolen | Authenticated replay | HTTPS, Secure/HttpOnly/SameSite, bounded expiry, revocation, recent auth | Active session can still expose ordinary content |
| Session fixation or privilege carryover | Attacker retains access | Rotate on login and privilege changes; revoke after recovery | Implementation omissions remain possible |
| Unlimited session persistence | Long compromise window | Idle and absolute expiry; no unlimited remember me | Longer writing sessions still create exposure |
| CSRF induces owner action | Unauthorized mutation | Django CSRF on every cookie-authenticated unsafe request, origin/config review | Browser or XSS compromise can bypass some protections |
| XSS acts through authenticated session | Archive disclosure or mutation | Output encoding, sanitization, CSP, HttpOnly cookies, authorization, recent auth | Same-origin script can perform ordinary authorized calls |
| Authorization omits Workspace scope | Cross-Workspace disclosure | Shared services/query patterns, explicit ownership, adversarial tests, optional later RLS | Future code paths can regress |
| Superuser implies creative authority | False Canon or provenance | Separate domain checks and events; prohibit silent approval | Database operators retain technical capability |
| Rate limiting locks out sole owner | Availability loss | Multi-dimensional bounded limits, owner-safe recovery, monitoring | Distributed attacks may still deny service |
| Generic errors impede diagnosis | Recovery friction | Authorized status views and bounded security events | Some uncertainty is intentional |
| Emergency procedure becomes bypass | Complete account takeover | Protected attributable access, evidence, rotation, revocation, review, separate documentation | One-owner separation of duties is limited |
| Authentication state restored from backup | Old sessions or credentials reactivate | Invalidate/reconcile credentials and sessions during restoration activation | Incorrect restore implementation can regress |
| Security logs expose sensitive metadata | Privacy loss | Allowlists, no manuscript/secret bodies, restricted access, bounded retention | IP and client metadata remain sensitive |
| Dependency compromise affects auth | Account takeover | Minimize packages, pin/review/update, advisories, tests, incident response | Supply-chain risk cannot be eliminated |

## Security and Privacy Review

- Security-sensitive: Yes; this ADR defines the primary account and authorization boundary.
- Primary references: `docs/architecture/security.md`, ADR-0001, ADR-0002, ADR-0003, and ADR-0004.
- Additional references: product vision, principles, scope, roadmap, data model, AI context, integrations, and the old Story Engine audit.

### Assets and trust boundaries

Protected assets include the owner account, password verifier, WebAuthn public credentials and metadata, TOTP seed if used, recovery-code verifiers, sessions, security events, private Workspace, manuscript, AI context, imports, exports, backups, restoration authority, provider credentials, and administrative access.

The browser, network, email provider, passkey synchronization service, external identity provider if later added, AI providers, integrations, imported content, restored artifacts, and operational clients are outside or across trust boundaries. Django mediates access. PostgreSQL is authoritative storage, not an authorization oracle independent of application meaning.

### Threats addressed

The model addresses credential stuffing, password phishing, MFA phishing, recovery abuse, account enumeration, session fixation, cookie theft, CSRF, stale authentication, unauthorized cross-Workspace access, ID manipulation, excessive job authority, administrator overreach, secret leakage, log leakage, malicious restoration, and provider dependence.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- bootstrap single use, partial failure, rerun, and unauthorized access;
- password validation, verifier upgrade, generic errors, rate limits, and session invalidation;
- WebAuthn registration/authentication origin, RP, challenge, signature, account binding, replay, and removal;
- multiple authenticators and recovery after loss of each factor;
- TOTP enrollment, replay, rate, clock, secret handling, removal, and fallback if enabled;
- recovery-code display-once, hashing, one-time use, regeneration, guessing, and containment;
- email and account enumeration resistance;
- session fixation, key rotation, multiple-device display, idle/absolute expiry, logout, and all-session revocation;
- recent authentication for every classified high-impact operation and no partial effect on failure;
- CSRF for forms, JSON, editor, AI, export, recovery, and administrative operations;
- altered stable IDs, cross-Workspace reads/writes, lifecycle, concurrency, and unauthorized-response behavior;
- proof that staff, superuser, job, command, AI, export, backup, migration, and restoration authority is bounded;
- exclusion of secrets, cookies, headers, IP detail beyond policy, and manuscript bodies from logs and events;
- export and backup exclusion of live sessions and plaintext recovery material;
- restoration that does not activate restored credentials or sessions; and
- emergency recovery rotation, revocation, evidence, owner review, and invariant reconciliation.

### Residual risk

The application server and database necessarily process authentication state and private content. A compromised server, database administrator, browser origin, owner device, password manager, or all recovery paths may defeat controls. A solo owner cannot always achieve organizational separation of duties. MFA and recovery reduce but cannot eliminate account takeover and lockout risk.

## Product and Architecture Alignment

### Product alignment

The recommendation protects the private archive, preserves authorial control, avoids provider custody of creative authority, supports recovery without silent bypass, and keeps Version 1 maintainable for a solo creator.

### Scope alignment

It supports secure single-user sign-in and sign-out without introducing teams, invitations, public registration, public sharing, organizational administration, or a role marketplace. Multiple device sessions support the actual desktop/laptop workflow without adding collaboration.

### ADR alignment

- ADR-0001: the browser is untrusted; all private operations and jobs are server-authorized.
- ADR-0002: Django owns authentication orchestration and application-service policy.
- ADR-0003: PostgreSQL stores authoritative account relationships and revocable sessions with explicit Workspace ownership.
- ADR-0004: stable IDs, session identifiers, consistency tokens, recovery codes, CSRF tokens, and idempotency keys do not grant domain authority; mutations retain concurrency and provenance rules.

### Architecture alignment

The decision preserves server-side Workspace scoping, narrow job and provider authority, secrets outside Git, synthetic development data, bounded logs, protected exports and backups, isolated restoration, and separation between operational access and creative approval.

### Normative-document impact

If accepted, the security architecture's authentication, MFA, session, authorization, recovery, and open-question sections should be reconciled with this decision, and the ADR index should be updated. No normative document is changed by this Proposed ADR.

## Migration and Portability

The local account and Workspace relationship are application concepts rather than deployment-provider identities. Password verifiers use supported Django representations and upgrade paths. WebAuthn credentials use standards-based public-key material. TOTP, if used, follows an interoperable standard. Recovery-code plaintext is never exportable after enrollment.

Migration to another supported framework, database, authentication package, or deployment must preserve account identity, Workspace grants, authenticator public material where interoperable, factor lifecycle, session invalidation, recovery state, and security-event meaning. Reauthentication or factor re-enrollment may be required when safe verifier migration is unavailable; it must be explicit and cannot silently weaken assurance.

Adding delegated identity later requires explicit account linking, collision handling, recovery rules, provider-subject stability, disconnection behavior, and a local exit path. Provider identity never becomes creative-record identity.

Exports of creative work exclude password verifiers, live sessions, TOTP seeds, recovery-code verifiers, reset tokens, provider credentials, and emergency secrets. Operational backups may need protected authentication state for disaster recovery, but restoration must invalidate or deliberately reconcile sessions, credentials, and recovery material before activation.

Old Story Engine data has no selected account or authorization authority. Migration of its creative material creates or maps Strange Novelty records through approved import provenance and does not import old settings, secrets, sessions, or implied creative approval.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Confirm deployment exposure, operator, administrative access, and bootstrap threat model.
- [ ] Define the protected initial-owner bootstrap workflow and invalidation evidence.
- [ ] Select supported Django password hashers and tuning at implementation time.
- [ ] Define minimum-length and compromised/common-password screening policy.
- [ ] Evaluate maintained Django-compatible WebAuthn packages and browser/device support.
- [ ] Decide WebAuthn user-verification, attestation, discoverable-credential, and attachment policies.
- [ ] Define multiple-authenticator enrollment and owner-facing labels.
- [ ] Decide whether TOTP fallback is necessary and define protected seed storage if so.
- [ ] Define recovery-code generation, count, format, hashing, display, regeneration, and containment.
- [ ] Define database-backed session schema/use, review metadata, cleanup, and owner revocation interface.
- [ ] Set documented idle and absolute session-expiry policies.
- [ ] Decide whether any bounded remember-me behavior is needed.
- [ ] Define session rotation and all-session revocation triggers.
- [ ] Define the recent-authentication operation matrix, windows, and factor requirements.
- [ ] Verify CSRF behavior for every cookie-authenticated state-changing route type.
- [ ] Define application/query-service authorization interfaces and Workspace-scoping conventions.
- [ ] Decide whether Django permissions, database roles, or PostgreSQL RLS add useful defense in depth.
- [ ] Define staff, superuser, service identity, job, command, AI, export, backup, migration, and restoration authority.
- [ ] Define generic authentication/recovery response behavior and rate-limit policy.
- [ ] Define security-event schema, retention, access, integrity, and privacy limits.
- [ ] Decide notification channels without treating email alone as recovery authority.
- [ ] Write and exercise the emergency recovery procedure before real private content is introduced.
- [ ] Define password reset, MFA recovery, account disablement, and credential/session rotation workflows.
- [ ] Define backup and restoration handling for authentication state without activating stale credentials.
- [ ] Add synthetic unit, integration, end-to-end, configuration, and adversarial tests described in this ADR.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes account creation, password or recovery-code generation, secret provisioning, Django initialization, package installation, schema creation, migration, middleware, route, form, template, API, deployment, or access to production data while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No account, credential, Django project, model, PostgreSQL table, migration, middleware, route, form, template, API, package, provider, or deployment configuration is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
