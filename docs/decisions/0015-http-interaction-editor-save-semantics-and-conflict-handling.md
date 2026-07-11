# ADR-0015: HTTP Interaction, Editor Save Semantics, and Conflict Handling

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 boundaries for private Django HTTP interaction, server-rendered editor loading, complete-content save requests, dual optimistic-concurrency preconditions, atomic immutable Scene Revision creation, durable idempotency, uncertain-outcome reconciliation, manual conflict handling, explicit save and optional coalesced autosave, HTML-first progressive enhancement, authentication, authorization and CSRF, response and redirect semantics, browser drafts and navigation, offline and interrupted requests, lifecycle and maintenance revalidation, private caching, safe rendering, resource limits, and accessible status communication, while exact Python, Django and browser versions, routes and URL shapes, form and structured-response schemas, endpoint-specific HTTP status codes, content-negotiation rules, idempotency-key format, fingerprint canonicalization and retention, transaction and locking details, autosave cadence and coalescing thresholds, revision-churn policy, conflict-review and diff interface, browser-draft persistence, cache directives, request/rate/concurrency/time limits, reauthentication UX, editor and JavaScript libraries, partial-page mechanism, accessibility implementation, telemetry fields, tests, and deployment configuration remain undecided.

## Decision Owners

- Decision owner: repository owner
- Author: Codex, acting as architecture-drafting assistant
- Reviewers: repository owner; product, accessibility, security, privacy, and implementation reviewers when assigned

## Context

Strange Novelty needs a dependable browser editing flow before Django views, forms, templates, JavaScript, or editor packages are created. ADR-0001 makes the browser untrusted; ADR-0002 selects server-rendered Django with optional progressive enhancement; ADR-0004 defines immutable complete Scene Revisions and dual optimistic-concurrency state; ADR-0005 requires authentication, authorization, sessions, and CSRF; and ADR-0006 defines normalized UTF-8 complete-content saves and non-authoritative browser drafts.

The owner may edit in multiple tabs or devices, navigate through browser history, lose connectivity, or retry after an ambiguous response. Even a single-user product therefore needs explicit stale-write and duplicate-delivery behavior. The interface must communicate uncertainty honestly without treating browser state, autosave indicators, or local storage as authority.

This ADR establishes one semantic path for HTML forms and enhanced requests. It does not create a public API, choose an editor or JavaScript framework, define exact HTTP routes, or authorize application implementation.

## Decision

If accepted, Version 1 will use the following interaction architecture.

1. Use conventional private Django HTTP endpoints and server-rendered HTML as the correctness baseline. JavaScript may progressively enhance the same application services.
2. Use GET only for safe retrieval/navigation and POST for authoritative browser mutations. Every cookie-authenticated state-changing request is CSRF-protected.
3. Resolve authentication, Account, Workspace, Scene, lifecycle, and operation authorization server-side. Browser-supplied identifiers and Workspace claims grant no authority.
4. Load the editor with Scene ID, current Revision ID, current Scene version, authoritative normalized text, lifecycle state, and bounded editing metadata.
5. Save requests carry Scene ID, expected current Revision ID, expected Scene version, complete proposed content with representation version where needed, a mutation-scoped idempotency key, and bounded intent such as explicit save or autosave.
6. The browser never allocates the authoritative Revision ID/number, Mutation Operation, timestamps, current pointer, or resulting Scene version.
7. The server authenticates, authorizes, scopes, validates CSRF, size, content format, normalization version, lifecycle, both concurrency preconditions, and idempotency before mutation.
8. A valid save atomically creates one immutable complete Scene Revision and Mutation Operation and advances the Scene current pointer/version. A failed, invalid, unauthorized, or stale save creates none.
9. Both expected Revision ID and expected Scene version must match current authoritative state. A mismatch is a conflict, not permission to overwrite.
10. Identical redelivery under the same idempotency key/fingerprint returns or reconciles the prior outcome. Reuse with changed content or intent fails visibly.
11. Delivery remains at-least-once in practice; no exactly-once claim is made. After timeout/interruption, reconcile the original key/result before retry.
12. A successful response returns the resulting Revision ID, Scene version, bounded timestamps/status, and redirect or representation metadata. “Saved” appears only after confirmed server success.
13. A conflict creates no authoritative mutation. It returns bounded authorized current-state metadata and may include current authoritative text when the actor remains authorized.
14. Preserve the rejected submitted draft in browser memory/form state. Version 1 does not require server-side conflict-draft storage or durable browser-local persistence.
15. Never automatically merge or offer a concurrency-bypassing “save anyway.” The owner manually compares, copies, edits against current state, and submits a new ordinary save with current preconditions.
16. Explicit save works without JavaScript. Optional autosave uses the identical mutation service, dual preconditions, idempotency, validation, and response semantics.
17. Autosave is debounced/coalesced and change-aware so it does not create revisions per keystroke. Exact cadence and thresholds remain later UX/performance choices.
18. Browser status distinguishes unsaved, saving, confirmed saved, conflicted, and failed/offline. It is accessible and advisory; queued or locally retained content is not saved.
19. Enhanced clients serialize outstanding saves or reconcile their responses. Version checks ensure a slow earlier request cannot overwrite a later accepted save.
20. Cancellation or navigation does not prove the server transaction was cancelled. Reload/reconcile authoritative state before changing the idempotency key or retrying ambiguous work.
21. Use Post/Redirect/Get for conventional successful form mutations where appropriate. Validation may rerender submitted data with field-level errors. Enhanced requests may return bounded structured results.
22. Keep domain outcomes consistent across HTML and structured responses. HTTP status codes communicate transport semantics but do not define domain state alone.
23. Use safe semantics conceptually: success/redirect; malformed request; unauthenticated; unauthorized/CSRF/non-disclosure; conflict; too large; semantic validation; rate limit; and generic server failure. Exact endpoint-specific codes remain implementation work.
24. HTML is the baseline representation. Bounded JSON or partial HTML may enhance it, but HTMX, Turbo, custom fetch, SPA frameworks, editors, and diff libraries remain unselected.
25. Private browser endpoints are not a public REST API or compatibility promise. Content negotiation is explicit and bounded.
26. Manuscript content is submitted only in protected request bodies, never URLs, query strings, path segments, referrers, analytics, cache keys, logs, metrics, traces, or Security Events.
27. Private responses use no shared caching; editor/save/conflict responses use no-store or narrowly justified private caching. Submitted and authoritative text is escaped as untrusted display content.
28. Bound request size, frequency, concurrency, processing time, and response size. Rejection is explicit and preserves the local draft where practical.
29. Authentication expiry may require reauthentication while preserving local submitted content where practical. Reauthentication never bypasses fresh authorization, CSRF, lifecycle, or concurrency checks.
30. Trashed Scenes ordinarily reject content edits. Archived Scenes require the selected lifecycle policy/transition. Racing lifecycle or maintenance changes fail safely on server revalidation.
31. Unsaved-change warnings and optional future browser storage improve recovery but are not persistence guarantees. Server-side drafts require a later lifecycle/privacy decision.
32. Save, error, offline, and conflict states are perceivable without color alone; forms identify errors; keyboard-only save and conflict recovery work; JavaScript is not required for correctness.

## Terminology and Boundaries

- A **browser draft** is proposed text in browser/form state; it is not authoritative Scene content.
- A **loaded Revision ID** records what was displayed. The **current Revision ID** is resolved from PostgreSQL when processing.
- The **expected Scene version** is a precondition. The **resulting Scene version** is allocated by the server.
- A request ID/correlation ID describes delivery; a Mutation Operation identifies accepted provenance.
- An idempotency key deduplicates one bounded intent and is not an authorization token.
- Duplicate delivery repeats the same fingerprint. Changed content is a new intent, not a retry.
- Timeout means unknown client observation, not known transaction failure.
- Request cancellation is transport behavior, not transaction rollback.
- Validation failure means unacceptable proposed input. Conflict means stale authoritative preconditions.
- Authentication establishes identity; authorization permits an operation; nonexistence disclosure is a separate privacy concern.
- CSRF failure and session expiry are distinct even when their public responses are deliberately generic.
- Explicit save is user-triggered; autosave is optional automated submission of changed draft state.
- A conflict draft is rejected proposed content; it is never a Scene Revision.
- Manual reconciliation is a human-authored new proposal, not automatic merge.
- “Save anyway” cannot mean bypassing current-state checks.
- HTTP response status describes a request outcome; authoritative state is determined from committed records.
- An HTML endpoint is a private application interface, not automatically a public API.
- Browser navigation/history is not domain revision history.
- A warning is not a persistence guarantee; local storage is not server authority.
- Current content comes from the explicit Scene pointer, not timestamp or revision-number maximum.
- Version 1 saves complete content rather than authoritative patches.
- Maintenance mode restricts operations globally but does not replace authorization.

## HTTP Interaction Principles

All private interactions use protected transport and Django session authentication. GET requests are safe and do not create revisions, Mutation Operations, or other domain mutations. POST requests express state-changing intent and are protected by CSRF and ordinary authorization.

Routes expose stable Scene identity only as a locator. Django resolves Workspace ownership and lifecycle. Request parsing, content negotiation, and errors are bounded. Browser or proxy behavior cannot relax server policy.

## Editor Load Contract

The editor load response provides only authorized data needed to edit: stable Scene ID; exact current Revision ID; current Scene version; authoritative normalized UTF-8 text; lifecycle state; format/normalization identifiers; and bounded title or editing metadata. The current pointer, not “newest” history, selects text.

Private editor responses must resist shared caching and history leakage. A loaded page is a snapshot and may become stale immediately; it never reserves or locks the Scene.

## Editor Save Contract

A save submits the complete proposed content, Scene ID, expected Revision ID, expected Scene version, supported content/normalization version, idempotency key, and bounded intent. The payload does not specify authoritative revision number, resulting version, actor authority, Workspace authority, or provenance outcome.

HTML forms and enhanced requests adapt into the same typed application command. Patch/diff data may support UI comparison later but is not authoritative input in Version 1.

## Optimistic Concurrency Preconditions

The mutation service compares both expected Revision ID and expected Scene version with the locked/conditionally updated current Scene. Both must match. This defends against stale tabs, duplicated pages, lifecycle/metadata changes included in the concurrency boundary, and accidental pointer/version inconsistency.

The final database write condition must make stale updates affect no current Scene row. No revision is retained when that condition fails.

## Successful Mutation Semantics

One short PostgreSQL transaction creates a server-generated immutable Revision and Mutation Operation, then changes the Scene pointer/version atomically. The normalized complete content is authoritative only after commit.

The response identifies the committed Revision and resulting Scene version. It may redirect to a canonical editor URL or return bounded HTML/JSON. Client state replaces its preconditions only from this confirmed result.

## Idempotency and Duplicate Submission

Each save intent uses a client-generated unpredictable idempotency key scoped by Workspace, actor/caller, Scene, and operation type. The server stores a privacy-safe canonical fingerprint, state, and result reference under ADR-0010.

Same key and fingerprint converges on the original outcome. Same key with different content/intent is rejected. Double clicks, form resubmission, browser retries, and response loss cannot create extra revisions for the same accepted intent.

## Retry and Uncertain Outcomes

Network failure, tab closure, or client cancellation can occur before or after commit. The browser retains the original key and reconciles by reloading/querying authorized state or replaying the identical request. It never assumes failure solely from missing response.

Changed content receives a new key only after the prior outcome is understood. Transient server retries preserve transaction/idempotency rules; validation, authorization, lifecycle, and conflict outcomes are not blindly retried.

## Conflict Detection

Any mismatch in expected Revision ID or Scene version is a concurrency conflict. A Scene lifecycle transition, restore, AI application, import, another tab save, or another authorized mutation can cause it.

Conflict detection occurs after current authentication/authorization and before revision insertion. The response does not confirm records outside the actor’s Workspace authority.

## Conflict Response and Review

An authorized conflict response returns safe current identifiers/version, current lifecycle, and enough current text/metadata for comparison. It also returns the submitted draft in the rendered form or relies on the browser’s retained copy; ordinary logs never carry either body.

Current text may be withheld if authorization changed. The UI clearly labels “your unsaved draft” and “current saved content.” A diff view may be added later but cannot execute or trust either side as markup.

## Manual Reconciliation

Version 1 offers discard, copy, compare, reload/current-edit, and submit-new-proposal actions. The owner decides what text to carry forward. A reconciled proposal uses the newest authorized preconditions and a new idempotency key.

It creates a normal new Revision and never rewrites, deletes, or relabels old revisions. There is no automatic merge, force update, or hidden last-write-wins path.

## Explicit Save and Autosave

Explicit save is always available and usable without JavaScript. Autosave, when enabled, is progressive enhancement over the same command. It coalesces rapid changes, avoids empty duplicate submissions, and limits revision churn.

The exact debounce, inactivity, minimum-change, maximum-wait, and revision policy remains undecided and must be tested with realistic writing. Autosave never suppresses visible failure/conflict state or redefine “saved.”

## Multiple In-Flight Requests

The enhanced editor normally permits one active save and queues/coalesces later local changes. If requests overlap, dual preconditions and idempotency make outcomes deterministic: only a request based on current state can commit.

Response arrival order is not authority. A late response cannot replace newer confirmed browser state without matching the latest accepted result.

## Authentication, Authorization, and CSRF

Every load and save authenticates the current session and authorizes Account/Grant/Workspace/Scene/lifecycle/operation. Authentication at editor load is insufficient for save. Session expiry requires reauthentication; the resubmission still rechecks concurrency.

All cookie-authenticated mutations use Django CSRF protection. CSRF tokens, session IDs, and stable IDs grant no domain authority. Unauthorized and inaccessible records use generic/404-style behavior where needed to prevent enumeration.

## Validation and Error Classification

Classify malformed syntax/encoding, unsupported format/version, content limit, semantic validation, authentication, authorization/non-disclosure, CSRF, concurrency, lifecycle/maintenance, rate/resource, and internal failures distinctly inside the application.

HTML errors preserve safe submitted values and identify affected fields. Enhanced errors use a bounded versioned error shape. No error echoes secrets or includes manuscript text in operational telemetry.

## HTTP Status and Response Semantics

Conceptual mapping is: 200 for successful represented outcomes; 303 for successful form redirect; 400 malformed; 401 or login redirect when unauthenticated according to endpoint style; 403 for authenticated denial or CSRF where disclosure is safe; 404 for non-disclosure; 409 conflict; 413 too large; 422 semantic invalidity where useful; 429 bounded rate rejection; and generic 500-class failures.

Exact choices may differ for HTML and structured endpoints, but domain error codes and behavior remain consistent. A redirect is emitted only after mutation success; a 2xx alone never substitutes for the returned authoritative identifiers.

## HTML Baseline and Progressive Enhancement

Server-rendered forms, field errors, conflict review, and explicit save form the baseline. JavaScript can add autosave, inline status, partial refresh, and comparison without owning authorization, normalization, concurrency, or provenance.

Partial HTML or bounded JSON endpoints call identical application services. No public REST API or SPA is introduced merely for editor convenience. Frontend technology remains deferred.

## Redirect and Navigation Behavior

Post/Redirect/Get avoids accidental browser resubmission after conventional successful saves. Redirect targets use stable Scene locators and never include content, tokens, or private titles.

Back, refresh, duplicate tab, restored session history, and navigation may reveal stale forms; version preconditions handle them. Navigation warnings reduce accidental loss but cannot guarantee persistence.

## Browser Drafts and Unsaved Changes

Browser memory/form state holds the active draft. It remains private, untrusted, and non-authoritative. Version 1 does not require localStorage, IndexedDB, service workers, or server-side drafts.

If local persistence is later selected, it needs origin isolation, retention, quota, multi-account/device, encryption exposure, extension threat, logout, and cleanup review. Server acknowledgement remains the only saved signal.

## Offline and Interrupted Requests

Offline editing may preserve text in the current page but does not create revisions. The UI announces offline/failed state and does not display saved. Reconnection first obtains/reconciles current authoritative identifiers.

Queued background synchronization is not selected. An interrupted request retains its key until the outcome is resolved.

## Lifecycle and Maintenance Interaction

Content save revalidates lifecycle in the transaction. Trashed Scenes reject ordinary editing. Archived editing requires the later explicit lifecycle policy, normally restoration or an authorized transition. Racing lifecycle changes cause safe failure/conflict.

ADR-0014 maintenance mode may block mutations while allowing safe retrieval and recovery. Leaving maintenance mode does not make stale browser preconditions current.

## Privacy, Caching, and Logging

Content appears only in protected bodies and authorized responses. It is excluded from URLs, referrers, analytics, logs, traces, metric labels, Security Events, error reports, and cache keys. Private titles receive the same treatment.

Editor, validation, and conflict responses are no-store by default or use narrowly justified private caching with reauthorization. Shared caches must not store them. Correlation and error codes are bounded and non-secret.

## Input, Output, and Rendering Safety

Decode, size-check, validate, and apply only ADR-0006 normalization. Content is untrusted plain text. Escape it in HTML and never execute it as markup, template, JavaScript, URL, path, SQL, shell command, or provider instruction.

Pasted/imported/provider text has no enhanced authority. Structured response parsing is schema/version bounded. Production errors are generic and safely escaped.

## Request and Resource Limits

Bound body bytes/characters, parsing cost, save rate, concurrent requests, transaction time, response size, and per-session/Workspace resource use. Apply inexpensive limits before expensive normalization or comparison.

Exact values and rate buckets remain operational decisions. Limit failures preserve authoritative state and the browser draft where practical; they never silently truncate content.

## Accessibility

The baseline uses labeled controls, associated field errors, logical focus order, keyboard operation, and persistent text status. Saving, saved, failed/offline, and conflict changes are announced through appropriate accessible status mechanisms without disruptive repetition.

Conflict review identifies each source, supports keyboard copying/editing, and does not rely only on color, animation, hover, drag, or diff decoration. Progressive enhancement preserves focus and works with assistive technology; reduced motion and browser zoom do not hide outcomes.

## Django Application Boundary

Django owns routing, session/CSRF checks, authentication, authorization, Workspace/lifecycle resolution, form/request validation, content negotiation, safe rendering, idempotency orchestration, concurrency command invocation, generic errors, redirects, cache headers, and maintenance enforcement.

HTML and structured adapters call one application service. Exact views, URLs, forms, middleware, templates, serializers, status codes, and JavaScript integration remain implementation work.

## PostgreSQL Boundary

PostgreSQL stores authoritative Scene/current pointer/version, immutable Revisions, Mutation Operations, and durable idempotency results. The atomic transaction and constraints reinforce dual-precondition mutation; the browser never connects directly.

PostgreSQL does not store browser navigation, transient save indicators, or local unsaved state as authority. Exact conditional-update SQL, isolation, locks, indexes, conflict-draft storage, and idempotency retention remain undecided.

## Rationale

Server-rendered HTML provides a complete, testable path with fewer client trust assumptions. Complete-content POST saves align with plain-text immutable snapshots. Dual preconditions prevent stale tabs and inconsistent pointer/version state. Durable idempotency resolves duplicate submission and uncertain responses without claiming exactly-once delivery.

Manual conflict recovery preserves authorial control and avoids unsafe automatic merges. Shared services keep enhanced and baseline behavior consistent. Privacy-safe bodies/caching and accessible status protect unpublished work while making the editor dependable.

## Decision Criteria

1. Prevent stale or duplicate writes from corrupting current Scene state.
2. Preserve immutable revisions, provenance, and atomicity.
3. Keep authorization, normalization, and lifecycle rules server-side.
4. Remain fully usable without JavaScript.
5. Communicate saved, uncertain, failed, and conflicted states honestly.
6. Protect manuscript content from URLs, caches, telemetry, and unsafe rendering.
7. Support multiple tabs/devices and interrupted networks safely.
8. Preserve accessibility and keyboard workflows.
9. Avoid premature frontend/public-API commitments.
10. Remain maintainable for one owner.

## Alternatives Considered

### Server-rendered HTML baseline

Selected for correctness, accessibility, and Django alignment.

### JavaScript-only single-page editor

Rejected for Version 1 because it makes JavaScript essential, duplicates policy adapters, and expands failure/accessibility complexity.

### Public REST API first

Rejected; browser needs do not justify a public compatibility/security surface.

### Private HTML with bounded structured enhancement

Selected. Both representations use the same service.

### PUT or PATCH semantics

Potentially expressive, but deferred. Version 1 HTML mutations use POST and complete-content domain commands.

### Complete-content POST saves

Selected to match immutable snapshots and ordinary forms.

### Blind overwrite

Rejected because stale tabs would silently lose work.

### Optimistic concurrency

Selected; single-owner multiple-tab conflicts are uncommon but consequential.

### Pessimistic locking

Rejected because browser locks become stale and impair interrupted/offline workflows.

### Automatic text merge

Rejected for Version 1; it can silently alter creative text.

### Manual conflict resolution

Selected to preserve authorial control.

### One precondition only

Revision-only or version-only is simpler but provides less invariant evidence. Both are selected.

### No idempotency or server-only heuristics

Rejected because time-window/content guesses cannot safely reconcile ambiguous delivery.

### Browser-generated idempotency keys

Selected with server scoping and fingerprint validation.

### Explicit save only

Safe baseline but less convenient. Retained as required fallback.

### Autosave only

Rejected because failure and JavaScript become too implicit.

### Explicit save plus optional autosave

Selected with identical mutation semantics.

### Revision per keystroke

Rejected due to write amplification and unusable history.

### Debounced or coalesced autosave

Selected conceptually; exact timing remains undecided.

### Conflict without current text

Safer after lost authorization but burdens authorized comparison. Used only when current text cannot safely be returned.

### Conflict with authorized current text

Selected to support manual review.

### Server-side conflict drafts

Deferred pending lifecycle, retention, privacy, and schema justification.

### Browser-retained submitted draft

Selected Version 1 baseline.

### Silent retry after timeout

Rejected because the original may have committed.

### Reconcile then retry

Selected with the same idempotency key.

### Query-string manuscript submission

Rejected because URLs leak broadly.

### Protected request-body submission

Selected.

### Raw exception pages

Rejected in production.

### Generic production errors

Selected with protected correlated diagnostics.

### Shared-cacheable editor responses

Rejected due to disclosure risk.

### No-store or bounded private caching

Selected.

### Select a frontend framework now

Rejected because semantics do not require one.

### Defer frontend mechanism

Selected while preserving progressive enhancement.

### Visual-only save state

Rejected as inaccessible and ambiguous.

### Accessible announced save and conflict state

Selected.

## Comparative Assessment

### Interaction architecture

| Strategy | Baseline resilience | Complexity | Decision |
| --- | --- | --- | --- |
| JavaScript-only SPA/API | Lower | High | Reject |
| Server HTML plus bounded enhancement | High | Moderate | Select |

### Save payload strategy

| Strategy | Snapshot alignment | Risk | Decision |
| --- | --- | --- | --- |
| Patch/diff authority | Low | Merge ambiguity | Reject V1 |
| Complete-content POST | High | Larger body | Select |

### Concurrency strategy

| Strategy | Lost-write safety | Decision |
| --- | --- | --- |
| Blind overwrite | None | Reject |
| Pessimistic browser lock | Brittle | Reject |
| Revision ID plus Scene version | Strong | Select |

### Idempotency and retry strategy

| Strategy | Ambiguous outcome | Decision |
| --- | --- | --- |
| Blind/new-key retry | Duplicates possible | Reject |
| Durable key/fingerprint, reconcile | Safe convergence | Select |

### Conflict-handling strategy

| Strategy | Author control | Decision |
| --- | --- | --- |
| Automatic merge/force save | Weak | Reject |
| Manual review with authorized current text | Strong | Select |

### Explicit-save and autosave strategy

| Strategy | Accessibility/resilience | Revision churn | Decision |
| --- | --- | --- | --- |
| Autosave only | Weak | Variable | Reject |
| Explicit only | Strong | Low | Baseline |
| Explicit plus coalesced autosave | Strong | Bounded | Select |

### Response format strategy

| Strategy | Duplication | Decision |
| --- | --- | --- |
| Separate API correctness | High | Reject |
| HTML plus bounded partial/JSON adapters | Low | Select |

### Browser draft persistence

| Strategy | Recovery | Privacy/complexity | Decision |
| --- | --- | --- | --- |
| Required local durable store | Better | Higher | Defer |
| In-page/browser form baseline | Basic | Lower | Select V1 |
| Server-side drafts | Strong | New authority/lifecycle | Defer |

### Privacy and caching

| Strategy | Disclosure risk | Decision |
| --- | --- | --- |
| URLs/shared caches/raw errors | High | Reject |
| Protected bodies, no-store/private, generic errors | Lower | Select |

### Accessibility and status communication

| Strategy | Assistive access | Decision |
| --- | --- | --- |
| Color/toast/JavaScript only | Poor | Reject |
| Persistent text, announced state, keyboard flow | Strong | Select |

## Evidence

### Repository evidence

- Product documents require trustworthy private drafting, authorial control, reversibility, and supported desktop/laptop browsers.
- Architecture documents require server policy, protected interactive flows, privacy-safe logging, immutable history, and conflict visibility.
- ADR-0001 through ADR-0014 establish the browser/Django/PostgreSQL boundary, server-rendered baseline, dual concurrency, authentication/CSRF, content format, schema, idempotency, operations, and privacy invariants used here.
- The architecture handoff identifies autosave, browser drafts, conflict recovery, and frontend mechanisms as deliberately undecided.
- The Story Engine audit shows direct current-row updates and selective snapshots without stale-write detection; those behaviors are not carried forward.

### Official guidance reviewed conceptually

- Django request/response, forms, CSRF, sessions, caching, security, transactions, and error guidance supports protected forms, validation, safe redirects, generic production errors, and atomic application services.
- HTTP semantics support safe/idempotent distinctions, redirects after POST, conditional conflict signaling, size/rate responses, and representation-specific behavior.
- OWASP authorization, CSRF, validation, output encoding, logging, session, denial-of-service, error, and cache guidance supports server reauthorization, protected bodies, safe rendering, bounded errors, and private caching.
- Recognized accessibility guidance supports labeled forms, error identification, keyboard interaction, focus management, and programmatically announced status messages.

Exact current versions and endpoint choices must be checked during implementation.

## Consequences

### Positive

- Stale tabs cannot silently overwrite newer work.
- Duplicate and ambiguous submissions converge safely.
- HTML and enhanced editor paths share one correctness model.
- Conflict recovery preserves the owner’s draft and immutable history.
- Private content avoids high-leakage URL/cache/telemetry paths.
- Accessible status communicates actual server persistence.

### Negative

- Dual preconditions and durable idempotency add request/schema complexity.
- Manual reconciliation requires owner effort.
- Complete-content saves use more bandwidth than patches.
- Without required local persistence, a browser crash can lose an unsaved draft.
- Coalesced autosave needs careful UX and performance testing.

### Neutral or Operational

- Exact routes, codes, response schemas, autosave cadence, limits, caching headers, and frontend mechanisms remain later work.
- Server conflict drafts and offline synchronization are not selected.
- A future public API would require a separate compatibility/security decision.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Lost update from stale tab | Dual preconditions and conditional atomic mutation |
| Duplicate Revision after timeout/double click | Durable scoped idempotency and fingerprint reconciliation |
| Autosave revision churn | Change detection, debounce/coalescing, bounded rate |
| Draft loss on crash | Clear unsaved state/warnings; evaluate privacy-safe local recovery later |
| Conflict text leaks | Reauthorize before return, protected bodies, no-store, no telemetry content |
| Slow earlier response corrupts UI state | Serialize saves and accept response only against tracked intent/result |
| CSRF/session confusion | Distinct internal classification and safe reauthentication flow |
| Accessibility regression in enhancement | HTML baseline, keyboard testing, announced persistent status |
| Resource exhaustion | Pre-parse size/rate/concurrency/time limits |
| Manual reconciliation mistake | Clear source labels, no force overwrite, new current-state submission |

## Security and Privacy Review

This ADR is security- and privacy-sensitive. Assets include manuscript drafts, authoritative text, session/CSRF state, stable IDs, conflict content, and idempotency evidence. Trust boundaries include browser-to-Django, shared/private caches, telemetry, and Django-to-PostgreSQL.

Threats include CSRF, enumeration, broken Workspace authorization, stale overwrites, duplicate submission, content injection, URL/referrer leakage, shared-cache disclosure, oversized requests, retry storms, and malicious text rendering. Controls are server reauthorization, CSRF, dual preconditions, durable idempotency, protected bodies, no-store/private caching, escaping, generic errors, limits, and privacy-safe telemetry.

Residual risks include unsaved browser data loss, compromised browser extensions/devices, implementation errors in response ordering, and inaccessible custom enhancement. Testing must cover multi-tab races, double submit, timeout-after-commit, expired sessions, CSRF, unauthorized IDs, lifecycle races, maintenance, oversized content, cache headers, escaping, keyboard operation, screen-reader status, and JavaScript-disabled flows.

## Product and Architecture Alignment

The decision advances the private Scene drafting journey and supports authorial control, trustworthy status, reversibility, privacy, and a narrow Version 1. It does not add rich text, public APIs, collaboration, automatic merge, durable local-first sync, or a frontend framework.

It preserves every accepted ADR through ADR-0014: server policy, PostgreSQL authority, immutable full snapshots, stable IDs, dual optimistic concurrency, CSRF/session authorization, normalized content, atomic schema boundaries, idempotency, privacy-safe operations, and maintenance behavior. No normative architecture amendment is required.

## Migration and Portability

The domain save command and outcomes remain independent of HTML/JSON adapters and frontend libraries. A later editor can reuse Scene ID, current Revision ID, Scene version, complete-content payload, and idempotency semantics.

Response schemas and content negotiation must be versioned before external compatibility is promised. Future local drafts, partial updates, public APIs, or richer content require migration/ADR review without weakening current revision identity and conflict behavior.

## Follow-Up Work

Before implementation:

1. define private routes, forms, response/error schemas, and endpoint-specific status codes;
2. define canonical request fingerprinting and idempotency retention;
3. decide exact autosave/coalescing/revision behavior from synthetic UX testing;
4. set request, rate, concurrency, transaction, and response limits;
5. define private cache headers and reauthentication/draft-preservation behavior;
6. design accessible HTML editor, validation, status, and conflict review;
7. test JavaScript-disabled, keyboard, screen-reader, multi-tab, timeout, duplicate, lifecycle, and maintenance paths;
8. decide whether privacy-safe browser or server conflict-draft persistence is justified;
9. update implementation references after application work is authorized.

## Implementation References

None. This ADR creates no code, views, URLs, forms, templates, JavaScript, APIs, models, migrations, tests, caches, or deployment configuration.

## Supersession and Amendment History

- 2026-07-11: Proposed and accepted after owner-directed architecture review.
- Supersedes: —
- Superseded by: —
