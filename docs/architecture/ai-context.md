# Strange Novelty Version 1 AI Context and Retrieval Architecture

## Purpose and Scope

This document defines the proposed Version 1 architecture for selecting, assembling, presenting, transmitting, retaining, and auditing context used by AI assistance in Strange Novelty. It defines one narrow AI capability and the rules that keep AI subordinate to the author-controlled Workspace.

It does not select an AI provider, model, embedding model, vector database, retrieval framework, application framework, or vendor. It does not authorize autonomous writing, unrestricted retrieval, general agents, provider tools, or direct provider access to application systems.

AI assists; the author decides. AI output is untrusted, reviewable material. It never becomes Canon automatically, and every retained result begins as AI suggestion.

## AI Design Goals

Version 1 AI behavior should:

- support a real scene-drafting workflow without becoming an autonomous storyteller;
- use the smallest task-specific context that can reasonably support the request;
- let the author understand what content will cross the AI-provider trust boundary;
- preserve distinctions among content state, creative context, provenance, chronology, reveal, and character knowledge;
- exclude unrelated, imported, legacy, deprecated, and machine-generated material by default;
- keep provider credentials and application authority server-side;
- produce reviewable suggestions without changing source content;
- preserve useful provenance without retaining sensitive request and response bodies indefinitely;
- make cost, scope, limits, and failure visible; and
- remain portable across future providers and implementation stacks.

## Core Principles

### The author controls the operation

An AI operation begins only through an explicit author action. The application may offer candidate context or explain why a source could help, but it may not silently submit content, expand scope, repeat a request, or apply a result.

### Context is task-specific and bounded

No AI operation may blindly ingest an entire Workspace, database, directory, backup, export, manuscript archive, book, or other broad collection. Context is assembled for one supported task from explicit selection, supported links, metadata, or a narrow search under documented limits.

### Content remains distinguishable

Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion remain distinct before, during, and after an AI operation. Inclusion in context does not promote authority, and omission does not change state.

### External processing is a trust-boundary crossing

An AI provider is outside the private application boundary. Only the AI gateway may send a bounded provider request. The provider receives request content, not credentials or access to the Workspace.

### Suggestions do not modify authority

Provider output is untrusted. Displaying, saving, copying, or editing it does not make it Canon. Applying any suggestion uses normal validation, concurrency, provenance, and state-transition rules.

### Failure preserves source content

Timeouts, provider errors, malformed responses, limit failures, cancellation, and partial operations leave authoritative content unchanged.

## Trust Boundaries

### Browser boundary

The browser presents task configuration, context preview, request status, and results. It is not trusted to authorize sources, enforce limits, classify state, or protect provider credentials. The server revalidates the task, Workspace ownership, source set, state rules, limits, and author session at submission.

### Application and retrieval boundary

The application server and its bounded retrieval components may read only the records required to assemble an authorized task. Retrieval is constrained by Workspace, supported source types, content states, creative context, spoiler and knowledge boundaries, and size limits.

### AI gateway boundary

The AI gateway is the sole outbound path to a provider. It converts an internal task package into a provider request, applies provider-independent safety and size rules, holds provider credentials, and normalizes the response.

### Provider boundary

The provider receives only the constructed request for one operation. It receives no direct database, filesystem, object-storage, search, export, backup, integration, administrative, or network access. Provider output has no application authority.

### Persistence and logging boundary

AI provenance records belong to protected application data. Operational logs and telemetry are separate and must not contain prompt bodies, response bodies, story excerpts, credentials, or unrestricted context manifests.

## Supported Version 1 AI Capability

### Selected capability: scene-focused review

Version 1 supports one explicitly invoked **scene-focused review**. The author selects one Scene as the primary source and asks the system to return a bounded set of observations and questions that may help revise that Scene.

The operation may consider:

- the selected Scene’s current revision;
- limited Scene metadata needed to identify its narrative position and state;
- a small number of author-selected Characters, Locations, or supported linked Scenes; and
- narrowly retrieved metadata or excerpts only when the author includes them through the previewed context.

The result may identify unclear motivation, internal inconsistency within the submitted context, missing grounding, possible link candidates, or questions for author review. It must not rewrite the Scene, claim a complete continuity analysis, inspect the full Book or Workspace, resolve ambiguity, change links, or classify content as Canon.

The selected capability is recommended because it supports the core drafting journey, works with a small explainable source set, can fail without altering content, and does not require semantic search or a mature continuity model.

### Alternative candidate: link suggestions

A narrower alternative would inspect one selected Scene and a bounded candidate list of Characters and Locations, then propose possible links. It is not the selected Version 1 capability because useful candidate discovery could pressure the first implementation toward broader retrieval, while scene-focused review remains useful with manual context alone. A future decision may choose this alternative only by updating scope and the relevant architecture documents before implementation.

## Explicit Invocation

- The author opens the AI action for a specific Scene and selects scene-focused review.
- The interface describes the task, expected output, possible exposure, and applicable limits.
- The application creates a draft context manifest but sends nothing externally.
- The author reviews the included sources and relevant exclusions.
- A distinct submit action authorizes that exact task and manifest version.
- The server validates the current authenticated session, reauthorizes the operation, and revalidates every source before sending. Recent authentication may be required only when justified by the security policy.

Opening a panel, selecting a source, saving a Scene, accepting a suggested context item, or retrying a page load is not submission consent. Automatic background submission and unreviewed retry are prohibited.

## Context-Source Types

Version 1 context sources are limited to:

- one primary Scene and its selected current revision;
- supported metadata for that Scene, including hierarchy position, content state, Creative Context, and provenance category;
- explicitly selected Character records;
- explicitly selected Location records;
- explicitly selected supported linked Scenes or bounded excerpts from them; and
- task instructions and system-authored definitions required to explain states and output constraints.

Search results, links, and metadata are discovery mechanisms, not automatic permission to transmit a source. Backlinks, revision history, audit records, imports, AI suggestions, deleted records, private objects, exports, backups, credentials, and operational logs are not context-source types unless a later approved capability defines a safe use.

## Context Selection Rules

Every context item must satisfy all of these rules:

1. It belongs to the authenticated owner’s Workspace.
2. Its type is supported by the scene-focused review task.
3. Its inclusion method is recorded.
4. It falls within the task’s count and size limits.
5. Its state and provenance are known and visible.
6. It satisfies the active Creative Context, spoiler, reveal, and character-knowledge boundaries.
7. It is not excluded by default or, if it is, the author has explicitly overridden that exclusion for this request.
8. It is read at a validated revision or concurrency version.
9. Its content is needed for the stated task.
10. It is represented in the final context manifest approved for submission.

Selection must be deterministic enough to explain and reproduce from the manifest while the referenced revisions remain available. When a source changes after preview, submission must refresh the preview or clearly require approval of the changed version.

## Context Manifests

A context manifest is the authoritative description of what the application intends to send. It is separate from the provider-specific prompt.

At minimum, a manifest records:

- operation identifier, Workspace identifier, task type, and creation time;
- primary Scene identifier and revision or concurrency version;
- each included source’s stable identifier, type, selected revision where applicable, state, Creative Context, and origin category;
- inclusion method: primary, manual, link-based, metadata-based, or search-based;
- bounded field or excerpt selection rather than an ambiguous whole-record claim;
- applied reveal, spoiler, character-knowledge, state, and provenance filters;
- explicit overrides and the author action authorizing them;
- excluded-source categories and relevant exclusion counts;
- estimated or measured request size;
- manifest version, instruction version, and integrity hash where useful; and
- submission, cancellation, completion, or failure status.

The manifest should use stable references and bounded metadata rather than duplicate full source text. It must not contain credentials. A manifest itself is private because identifiers, titles, relationships, and selection patterns may reveal story information.

## Context Preview

Before submission, the author must be able to understand the context being used.

The preview should show:

- the task and primary Scene;
- each included source with type, recognizable label, state, provenance category, and inclusion reason;
- whether the full selected field or a bounded excerpt will be sent;
- the active spoiler, reveal, character-knowledge, and Creative Context boundaries;
- any imported, legacy, deprecated, speculative, or AI-generated source included by explicit override;
- material excluded by rule in a summarized, non-misleading form;
- request size and applicable cost or usage estimate when available; and
- controls to remove optional sources, inspect why a source was selected, cancel, or submit.

The preview need not reveal hidden secrets or reproduce all submitted prose a second time, but it must not describe a broad or dynamic rule so vaguely that the author cannot understand the exposure. The submitted manifest must match the previewed manifest.

## Inclusion and Exclusion Rules

### Included by default

The primary Scene’s selected current revision and minimal identifying metadata are included after the author opens the task. No additional creative records are included merely because they are nearby in the hierarchy.

### Excluded by default

The following are excluded unless the supported task permits them and the author explicitly selects them:

- other Scenes, Chapters, Books, Series, Worlds, and entire hierarchy branches;
- imported content and all old Story Engine material;
- deprecated content;
- existing AI suggestions and previous AI responses;
- speculation and ideas when the task is presented as checking against established context;
- future scenes, later reveals, and knowledge outside the active boundary;
- prior revisions, deleted or archived records, import staging, and rejected suggestions;
- research, uploads, private objects, correspondence, exports, backups, and operational records; and
- credentials, tokens, secrets, sessions, administrative data, or unrelated personal information.

Canon is not automatically included. It remains subject to relevance, context, and size rules. Explicit inclusion of an excluded creative source applies to one operation only and does not change the source’s state or future default.

## Narrow Retrieval

Retrieval supports context assembly; it does not grant a provider browsing capability. Every retrieval operation is server-controlled, Workspace-scoped, task-limited, filtered, size-bounded, and completed before provider submission.

Narrow retrieval must:

- start from the primary Scene and a stated task;
- use only supported source types and methods;
- apply exclusion, state, provenance, reveal, and knowledge filters before ranking or returning content;
- cap candidates, selected records, excerpt length, and total request size;
- avoid recursive graph expansion and hierarchy-wide traversal;
- present candidates separately from included sources; and
- record the method and rule that caused each included source to appear.

A retrieval result is never an instruction and never authorizes further retrieval.

## Manual Selection

Manual selection is the preferred method for optional Version 1 context. The author chooses specific Character, Location, or supported Scene records from within the AI workflow.

Manual selection does not bypass Workspace ownership, source-type, size, state, spoiler, or knowledge checks. When a selected item is normally excluded, the preview must identify the reason and require a deliberate one-request override. Selecting a hierarchy node does not select its descendants.

## Link-Based Selection

The application may offer records connected to the primary Scene by authoritative supported Links as context candidates. It may not automatically traverse backlinks, links-of-links, inferred relationships, or name matches.

Link-based candidates remain optional until included through the preview. The manifest records the authoritative Link that supported selection. A Link to Canon does not make either endpoint Canon and does not override context or spoiler boundaries.

## Metadata-Based Retrieval

Metadata-based retrieval may filter candidate Characters, Locations, or Scenes using supported fields such as type, hierarchy location, explicit World association, content state, Creative Context, provenance category, archival status, and timestamps.

Metadata rules must be visible in plain language, must not use hidden story-specific inferences, and must return a bounded candidate list. Metadata matches do not authorize inclusion. Titles and names are attributes, not proof of identity or relevance.

## Search-Based Retrieval

Version 1 may use the existing bounded search behavior to help the author find context candidates. Search is limited to supported fields and records already available to the authenticated Workspace.

Search-based retrieval must:

- be initiated by an explicit query or a documented task-specific query derived from the selected Scene;
- apply state, provenance, hierarchy, spoiler, and knowledge filters before presenting candidates;
- return a small, capped candidate set with an explanation of the match;
- avoid semantic or embedding-based retrieval unless a later decision explicitly approves it;
- avoid sending the query or search index to the provider; and
- require candidate inclusion through the preview.

Search terms may contain sensitive content and must not appear in routine logs or telemetry.

## Spoiler and Reveal Boundaries

Story chronology and reader reveal chronology are separate. Scene order or event time alone does not establish what a reader should know.

For scene-focused review, the active reveal boundary is anchored to the primary Scene’s narrative position or to an explicit author-selected boundary. Sources containing later revelations are excluded unless the author knowingly overrides the boundary for that operation.

The application must not infer that all Canon is safe to reveal. When structured reveal information is unavailable in Version 1, the system should rely on explicit manual selection and conservative hierarchy filters rather than claim spoiler safety. The preview must communicate uncertainty and any override.

AI output must not be presented as spoiler-safe beyond the supplied boundary. A model inference can still anticipate future material; this limitation must be clear to the author.

## Character-Knowledge Boundaries

Character knowledge is distinct from Canon and reader revelation. A Canon fact is not automatically known by every Character, and presence in an earlier Scene is not sufficient proof of knowledge.

Version 1 does not yet provide a complete character-knowledge model. Therefore scene-focused review must not claim that a Character knows or cannot know a fact unless that knowledge is explicitly represented in selected context. When the task concerns a point-of-view Character, the author may define an allowed knowledge boundary and manually include supporting sources.

Material outside that boundary is excluded unless the author explicitly permits it for the request. The response should phrase uncertain knowledge as a question or observation for review, not as authoritative continuity correction.

## Canon and Content-State Handling

- State metadata accompanies every creative source in the manifest and, where helpful, in provider instructions.
- Canon is authoritative only within its recorded Creative Context; it is not universal and is not automatically included.
- Draft is editable authored material, not established truth.
- Speculation and Idea are possibilities and must not be presented as facts.
- Imported content remains imported even when edited or included.
- Deprecated content is historical or superseded and excluded by default.
- AI suggestion remains machine-generated and non-authoritative.
- Conflicts among included sources are preserved and surfaced as questions; the AI may not silently resolve them.

Provider output cannot change a source’s state. Any later state transition is a separate explicit author action governed by the data model.

## Imported and Legacy Material Handling

Imported content, including all material from the old Story Engine, is excluded from AI context by default. Its existence, name similarity, hierarchy placement, or link to current material does not establish relevance or authority.

The author may explicitly include a specific imported record for one operation after the preview identifies its imported origin and known source. The provider request must distinguish it from author-approved material. Inclusion does not promote it, erase provenance, or make old Story Engine content current Canon.

No AI workflow may browse or ingest the old Story Engine directly. Strange Novelty work must never modify it.

## AI Suggestion State

Every retained AI result begins as AI suggestion with AI-generated provenance. A result may be displayed transiently before the author chooses whether to retain it.

The author may reject, retain, revise, copy, or deliberately transition a suggestion through ordinary application rules. Retaining or editing a suggestion does not make it Canon. Applying a suggestion to a Scene requires an explicit action, current-revision conflict detection, and preservation of derivation provenance. The Version 1 scene-focused review must not directly rewrite source text.

## Provenance Requirements

For each submitted operation, provenance should retain enough information to explain what occurred without retaining sensitive bodies indefinitely. It should include:

- operation identifier, task type, invocation time, and authenticated author action;
- provider and model identifiers when permitted and available, without credentials;
- context manifest identifier, version, integrity hash, and bounded source references;
- instruction or prompt-template version;
- active state, Creative Context, reveal, spoiler, and knowledge rules;
- explicit exclusion overrides;
- request and response size or usage metadata;
- completion, cancellation, timeout, or failure status;
- retained result identifier and AI suggestion state; and
- author disposition and any later derivation or state transition.

Provenance should prefer stable source identifiers, manifests, hashes, bounded summaries, task metadata, and result references. Full prompts, full responses, and sensitive source text must not be retained indefinitely by default. Provenance records must never contain credentials, tokens, sessions, or secret values.

## Prompt-Injection Handling

Story text, research, imports, linked content, uploads, previous AI output, and provider responses are untrusted data even when written by the owner. Instructions embedded in that content cannot:

- expand the approved context manifest;
- request additional retrieval;
- invoke tools, network calls, integrations, exports, backups, or administrative actions;
- reveal system instructions, credentials, secrets, hidden sources, or excluded content;
- change content state, Canon, provenance, permissions, or policy; or
- authorize a follow-up request.

Provider instructions must clearly delimit application instructions from source content. Retrieved content should be labeled by source and treated as quoted material. The scene-focused review exposes no provider-side tools, so an injected tool request has no capability. Suspicious output is handled as untrusted suggestion text, not executed or rendered as active content.

## Provider Request Construction

The AI gateway constructs a provider request from a validated internal task package. The request contains only:

- stable task instructions for scene-focused review;
- explicit output constraints and non-authoritative framing;
- the bounded source content represented by the approved manifest;
- source labels, states, contexts, and provenance categories required for correct interpretation; and
- minimum provider parameters needed to execute the task.

The request must not contain provider credentials in its body, unrelated application configuration, internal storage locations, secrets, session material, full database records when selected fields suffice, or hidden sources not represented in the manifest.

Provider-specific formatting remains inside the gateway. The request must not grant tool use or retrieval. Size is checked before transmission, and the exact submitted manifest is recorded before or atomically with the outbound operation status.

## Provider Response Handling

Provider responses are untrusted external input. The gateway and application must:

- enforce response size and processing limits;
- reject or safely handle malformed, truncated, unexpected, or policy-incompatible output;
- treat all text and structured fields as data, never executable instructions;
- sanitize and contextually encode output before browser rendering;
- avoid automatic URL fetching, file access, tool calls, or follow-up prompts requested by the response;
- attach operation provenance and classify retained output as AI suggestion;
- present uncertainty and source limitations rather than imply complete knowledge;
- avoid replacing, revising, linking, or reclassifying source records automatically; and
- preserve the selected Scene’s concurrency version so any later author action detects intervening edits.

Claims and citations produced by the model are not trusted references unless the application can map them to included sources. Unknown references must be shown as unverified or omitted according to the task contract.

## Failure Behavior

Provider unavailability, authentication failure, rate limits, timeouts, cancellation, invalid manifests, changed source revisions, oversized context, malformed output, safety rejection, storage failure, or network interruption must:

- leave authoritative content, links, states, and provenance unchanged;
- avoid silently retrying an externally billed request;
- report a clear, privacy-conscious status without exposing source content or credentials;
- distinguish not-submitted, submitted, unknown, succeeded, failed, and safely retryable states;
- avoid retaining partial output as an accepted suggestion;
- permit an explicit retry only after the author can confirm the task and current context; and
- record bounded operational and provenance status needed to diagnose duplicate or ambiguous requests.

If submission outcome is unknown, the system must not assume failure and automatically resubmit. Ordinary workspace use must remain available when the provider is unavailable.

## Retention and Deletion

- Draft manifests not submitted should expire after a documented short period.
- Submitted manifests and bounded provenance may be retained as needed to explain results and author actions.
- Full prompt bodies, full response bodies, and duplicated sensitive source text are not retained indefinitely by default.
- Transient provider-request content should be released after completion unless a documented, approved need requires short retention.
- Rejected, cancelled, failed, and unretained results need explicit short retention and disposal rules.
- Retained AI suggestions follow protected application lifecycle, export, backup, deletion, and restoration rules.
- Deleting a suggestion does not erase required minimal audit or provenance facts, but retained facts must minimize sensitive content.
- Provider-side retention and deletion capabilities must be evaluated before provider selection and communicated accurately; application deletion cannot promise deletion beyond provider capabilities.
- Backups may retain deleted AI records until backup expiration, which must be disclosed honestly.

Exact retention periods remain open decisions.

## Cost and Usage Visibility

Before submission, the interface should show a useful estimate or qualitative size indication based on the selected context. After completion, it should record and display available request, response, and cost or usage information in understandable terms.

Provider billing units must not leak into the core domain model beyond normalized usage metadata. Estimates must be labeled as estimates. The application must prevent hidden background use, uncontrolled retries, and recursive AI calls. Usage metadata must not include prompt or response bodies in routine telemetry.

## Rate and Size Limits

Version 1 must define enforceable limits for:

- one primary Scene per operation;
- optional source count by type;
- characters or bytes per source and in total;
- excerpt size and number;
- provider input and output size;
- concurrent operations per Workspace;
- submissions over a time window;
- retry attempts; and
- cost or usage over a configured period where provider data permits.

Limits are enforced server-side before retrieval, before submission, and while processing the response. Exceeding a limit fails visibly and does not silently truncate in a way that misrepresents context. The author may remove sources or shorten scope; the system may not broaden limits automatically.

## Privacy and Security Requirements

- Only the authenticated owner may initiate an AI operation or view its private manifest, result, usage, or provenance.
- Authorization and Workspace scoping are enforced server-side for every source and operation.
- Provider credentials stay server-side and never appear in browser configuration, source control, logs, manifests, exports, or provenance.
- Providers receive no direct database, filesystem, object-storage, search, export, backup, integration, administrative, or Workspace access.
- Context and responses use protected transport and protected storage appropriate to private creative content.
- Operational logs, analytics, error reports, traces, and telemetry exclude story text, prompt bodies, response bodies, search terms, credentials, and sensitive manifests.
- Third-party provider retention, training use, human review, geographic processing, subprocessors, and incident terms require review before selection.
- Request and result rendering follows CSRF, XSS, injection, request-forgery, and safe-output requirements in the security architecture.
- AI context is never committed to Git. `private-data/`, manuscripts, artwork, databases, exports, and backups remain outside version control.
- Security failures fail closed and never expand context or authority.

## Testing Expectations

Before Version 1 acceptance, testing should cover:

- explicit invocation and absence of background or accidental submission;
- exact agreement among preview, manifest, retrieved sources, and provider request;
- Workspace authorization and altered-identifier attempts for sources, manifests, results, and retries;
- manual, link-based, metadata-based, and narrow search candidate behavior;
- source count, excerpt, total request, response, concurrency, rate, retry, and cost limits;
- default exclusion of imported, old Story Engine, deprecated, prior AI, future-reveal, and out-of-bound knowledge material;
- one-request overrides and their visible provenance;
- preservation of all content-state and Creative Context distinctions;
- spoiler and character-knowledge boundary behavior, including uncertainty when structured data is absent;
- source changes between preview and submission;
- prompt injection in Scenes, imports, metadata, prior AI output, and provider responses;
- proof that provider requests have no tools or direct application access;
- malformed, oversized, truncated, hostile, duplicated, delayed, and unexpected responses;
- timeouts, cancellations, rate limits, authentication errors, unknown submission outcomes, and explicit retry;
- unchanged authoritative content after every failure path;
- output sanitization, safe rendering, and refusal to execute response-supplied URLs or instructions;
- AI suggestion classification, concurrency checks, provenance, retention, deletion, export, backup, and restoration;
- provider credential isolation and absence of sensitive content from logs and telemetry; and
- ordinary workspace availability during provider outage.

Tests should use synthetic story data. Representative adversarial tests should verify that embedded instructions cannot expand context, invoke capabilities, reveal excluded sources, or alter policy.

## Security Invariants

- AI assists; the author decides.
- AI output never becomes Canon automatically.
- Every retained AI result begins as AI suggestion.
- Every AI operation is explicitly invoked by the authenticated owner.
- No operation blindly ingests an entire Workspace, database, directory, backup, export, Book, or manuscript archive.
- Every submitted context is task-specific, bounded, represented by a manifest, and understandable to the author.
- The submitted manifest matches the previewed and authorized manifest.
- Optional context comes only from manual selection, supported links, metadata, or narrow search.
- Retrieval is server-controlled and never delegated to the provider.
- Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion remain distinguishable.
- Imported content and old Story Engine material are excluded by default and require explicit one-operation selection.
- Story chronology, reader reveal chronology, and character knowledge remain separate.
- Future reveals and knowledge outside the allowed boundary are excluded unless the author explicitly permits them.
- Prompt injection in story text, research, imports, metadata, or AI output is untrusted and cannot expand context, invoke tools, reveal secrets, or alter policy.
- Provider credentials remain server-side.
- Providers receive no direct database, filesystem, storage, search, export, backup, integration, administrative, or Workspace access.
- Provider responses have no application authority and cannot change content automatically.
- Provider failure leaves authoritative content unchanged.
- Full prompts, full responses, and sensitive source text are not retained indefinitely by default.
- Provenance prefers stable source identifiers, manifests, hashes, bounded summaries, and task metadata.
- Sensitive AI content does not appear in routine logs, analytics, errors, traces, or telemetry.
- The old Story Engine remains reference-only and is never modified.

## Explicit Non-Decisions

This document does not decide:

- the AI provider, model, model family, access method, or processing region;
- the final provider privacy, retention, training-use, human-review, or subprocessor terms;
- an embedding model, vector database, semantic-search system, reranker, or retrieval framework;
- the application framework, language, AI library, orchestration framework, or prompt-management product;
- whether link suggestions become a later separate capability or an output of a future expanded scene-review capability;
- the exact scene-review prompt wording or output schema;
- the editor or Scene content format;
- exact source, excerpt, request, response, rate, concurrency, cost, or retention limits;
- the search implementation or ranking method beyond the bounded Version 1 rules;
- a complete spoiler, reveal, timeline, or character-knowledge model;
- the final context-preview interface;
- the provider-independent usage normalization schema;
- prompt, response, manifest, suggestion, or failed-operation retention periods;
- the final encryption, secret-management, logging, monitoring, or deployment products; or
- any broader AI capability, autonomous agent, provider tool use, general Workspace assistant, or unrestricted retrieval.

Significant durable choices require review against product, data, security, privacy, portability, cost, and recovery requirements and should be recorded in architecture decision records before implementation depends on them.

## Open Questions

1. Which acceptance criteria confirm that scene-focused review is sufficiently narrow, explainable, and useful for the first implementation milestone?
2. Which exact observations and questions are in scope for scene-focused review, and which would imply unsupported continuity analysis or rewriting?
3. Which Scene fields and metadata are required, and is the full current revision always necessary?
4. How many optional Characters, Locations, and linked Scenes may one request include?
5. Are linked Scene excerpts supported in Version 1, and how are excerpt boundaries chosen and previewed?
6. Which state and Creative Context filters apply to the default scene-review task?
7. What explicit interaction is required to override imported, legacy, deprecated, speculative, AI-generated, spoiler, or knowledge exclusions?
8. How is the reveal boundary anchored when narrative order differs from Chapter and Scene order?
9. What conservative behavior applies until structured reveal and character-knowledge records exist?
10. Can metadata- or search-derived candidates be generated automatically after the author opens the task, or must the author initiate each discovery method?
11. What bounded search fields and ranking explanation are sufficient without semantic retrieval?
12. What manifest fields and hashes are needed for reproducibility, privacy, and later audit?
13. How should the interface respond when a source changes between preview and submission?
14. What provider-request structure best separates instructions from untrusted creative content?
15. What response structure makes uncertainty, source use, and non-authoritative status clear?
16. Which provider retention, training-use, human-review, geographic, deletion, subprocessor, and incident terms are acceptable?
17. Which prompt and response content, if any, must be retained temporarily for troubleshooting, and who may access it?
18. How long are draft manifests, failed operations, rejected results, retained suggestions, and normalized usage records kept?
19. What exact request, response, concurrency, retry, rate, and cost limits protect privacy and spending without disrupting normal use?
20. How should unknown provider submission outcomes be reconciled without duplicate billing or duplicate suggestions?
21. Which security and privacy events require alerts in a low-maintenance single-user deployment?
22. How are retained AI records represented in exports and backups, and what is intentionally omitted?
23. Which representative prompt-injection and boundary-escape cases must block Version 1 acceptance?
24. Which decisions require architecture decision records before application code begins?
