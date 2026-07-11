# ADR-0006: Scene Content Representation and Editor Persistence Boundary

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 Scene content representation and editor persistence boundary, while the exact editor package, frontend framework, physical schema, Unicode normalization form, content limits, autosave policy, browser-draft storage, pasted-content transformation rules, rendering details, search/count algorithms, export formats, and migration tooling remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; writing/editor, accessibility, Unicode, Django, PostgreSQL, security, privacy, search, AI-context, export, import, backup, restoration, and migration perspectives

## Context

Strange Novelty must preserve creative text exactly enough that the author can write, compare, recover, export, migrate, and restore it without the browser, editor package, rendering engine, or external provider becoming authoritative. Version 1 needs a dependable writing workflow, not a full word processor or a premature rich-text platform.

ADR-0001 makes the browser untrusted and places all authoritative reads and writes behind server-side application services. ADR-0002 selects Django as the server framework and policy boundary. ADR-0003 selects PostgreSQL as the authoritative relational database. ADR-0004 distinguishes stable Scene identity from immutable Scene Revision identity, selects append-oriented full snapshots, and requires saves to use a Scene version/current-revision token in one atomic revision-and-pointer transaction. It prohibits silent last-write-wins and automatic merge. ADR-0005 requires every private operation to be authenticated, authorized, Workspace-scoped, revalidated server-side, and CSRF-protected where cookie-authenticated.

Browser-local drafts are non-authoritative. AI output is suggestion data, and applying it requires explicit owner action through the ordinary save boundary. Jobs, imports, exports, backup, migration, and restoration receive bounded authority. No browser, editor, provider, derived index, or exported rendering becomes the source of creative truth.

The selected content representation affects revision comparison, normalization, rendering, security, search, AI context, exports, imports, backups, restoration, and later editor migration. Deferring it until an editor is selected would allow a package-specific format or browser DOM to become an accidental durable contract.

The decision must distinguish:

- content representation from editor implementation;
- authoritative content from rendered presentation;
- plain text from Markdown interpretation;
- line-ending normalization from creative rewriting;
- Unicode normalization from spellcheck or autocorrect;
- committed Scene content from Scene metadata;
- committed revisions from browser drafts;
- autosave requests from local draft persistence;
- editor undo from durable revision restoration;
- current revision content from rejected conflict content;
- revision content from provenance and audit;
- search text and excerpts from the authoritative source;
- AI context projection from the complete revision;
- export format from storage format;
- backup from export;
- content encoding from database column type; and
- representation migration from ordinary editing.

Content representation defines the durable meaning and serialization rules for a committed value. Editor implementation defines how the browser lets the author manipulate a proposed value. A textarea, Markdown editor, or rich-text editor could theoretically edit the same durable representation, while one editor-native document could require a different representation. This ADR selects the former contract without selecting the editor.

Exact Python, Django, PostgreSQL, editor, sanitization library, Markdown processor, frontend package, browser, export library, storage schema, and deployment remain undecided unless a later accepted decision selects them.

## Decision

If accepted, Version 1 will use the following model.

1. Each committed Scene Revision contains one complete authoritative content value represented as normalized UTF-8 plain text.
2. Paragraphs and line breaks are preserved. Markdown punctuation, HTML-like tags, and editor syntax remain literal text and have no authoritative formatting meaning.
3. Every revision records a stable content-format name and version and a normalization version alongside the content.
4. Accepted line endings are normalized deterministically to one canonical internal convention. One Unicode normalization form will be selected after compatibility testing and recorded in the normalization version.
5. Normalization changes only documented representation-level details. It never silently trims the whole document, collapses blank lines, reflows paragraphs, changes case or punctuation, autocorrects spelling, substitutes typography, or rewrites creative text.
6. Invalid encoding, null characters, unsupported controls, dangerous bidirectional controls where policy requires, unsupported format versions, and content beyond documented limits are rejected safely.
7. The browser receives committed content with the accepted Scene version/current-revision token. A save submits the complete proposed content and observed token; no browser patch or diff is authoritative.
8. Django revalidates authentication/session state as required, authorization, Workspace and Scene ownership, CSRF, content format, size, supported characters, normalization, concurrency, and idempotency before committing.
9. A successful save creates one immutable full-snapshot Scene Revision and atomically advances the Scene current-revision pointer and integer version. A failed save creates no authoritative revision.
10. Browser drafts, autosave buffers, undo stacks, cursor and selection state, scroll position, spellcheck state, and editor preferences are not committed Scene content. A saved state appears only after server acknowledgment.
11. A stale save becomes a conflict. Its submitted content is preserved for bounded recovery but does not become an authoritative Scene Revision automatically.
12. HTML rendering, counts, excerpts, search text/vectors, previews, comparison views, AI context slices, and non-plain-text exports are derived, rebuildable projections tied to a source revision when retained.
13. AI receives only explicitly authorized, bounded text derived from committed revisions or an explicitly authorized submitted draft, with provenance, source revision identity where applicable, and format version.
14. Author-facing plain-text export preserves authoritative text under documented encoding and line-ending rules. Structured archives preserve content, identities, lineage, pointers, representation versions, and integrity metadata. HTML, Markdown, DOCX, PDF, and other outputs are derived exports.
15. Import converts external material into Version 1 plain text through an explicit staged transformation with provenance and warnings. Restoration of the same archive preserves exact authoritative revision content and representation metadata.
16. Future rich text requires a later ADR and migration plan preserving every revision, identity, lineage, comparison, export, and restoration invariant.

## Authoritative Scene Content

Each committed Scene Revision contains exactly one complete authoritative Scene content value. In Version 1 that value is UTF-8 plain text after the documented normalization pipeline.

The value may contain ordinary Unicode letters, combining marks, digits, punctuation, symbols, spaces, tabs where allowed by later policy, and line breaks. It represents what the author committed, not a browser DOM tree, HTML fragment, Markdown abstract syntax tree, editor operation log, or rendered page.

Plain text does not mean ASCII, English-only text, typography removal, or whitespace collapse. It supports multilingual names, dialogue punctuation, symbols, and other ordinary creative writing characters subject to explicit security and compatibility rules.

Markdown syntax typed by the author remains literal authoritative text. A sequence such as a heading marker or emphasis delimiter is not stored as formatting semantics. A later optional presentation may interpret it deliberately, but that interpretation is derived and cannot change the source without an explicit ordinary save.

HTML tags are not trusted or stored as authoritative rendered markup. Tag-looking text remains text. Rendering escapes it so manuscript content cannot introduce elements, scripts, event handlers, styles, URLs, or active browser behavior.

Scene metadata—title, hierarchy, lifecycle, state, current revision pointer, timestamps, version, provenance, relationships, and contextual Canon—is not embedded in the content value merely for editor convenience. It remains separately modeled and authorized.

## Content Format and Versioning

Every Scene Revision records a stable format identifier and format version for its authoritative content. Version 1 uses a stable name meaning normalized UTF-8 plain text; the exact serialized label is defined before implementation and remains independent of a database column name or editor package.

Every revision also records or unambiguously resolves the normalization version used to produce its stored value. Format version explains how to interpret content. Normalization version explains which deterministic input-to-authoritative transformation was applied.

The format contract includes:

- Unicode text encoded as UTF-8 at external byte boundaries;
- one canonical internal line-ending convention;
- one selected Unicode normalization form after compatibility testing;
- explicit treatment of byte-order marks, nulls, invalid sequences, controls, and bidirectional controls;
- preservation rules for ordinary whitespace and punctuation; and
- deterministic validation and normalization ordering.

The database may use a PostgreSQL text-compatible type, but database column type is a physical storage choice, not the content encoding contract. PostgreSQL internally storing character data does not by itself define export bytes, normalization, permitted controls, or editor semantics.

A revision never changes interpretation because a later deployment upgrades a library or browser. Material changes require a new format/normalization version and a reviewed migration or compatibility path.

## Unicode and Line-Ending Normalization

The server accepts request bytes only through a supported decoding path and normalizes all accepted line endings to one canonical internal convention. External export may deliberately use another documented convention, but conversion is explicit and reversible with respect to logical line breaks.

One Unicode normalization form will be chosen after testing representative creative text, combining sequences, compatibility characters, search behavior, copy/paste sources, imports, exports, and round trips. This ADR does not select NFC, NFD, NFKC, or NFKD.

Unicode normalization is a representation-level canonicalization of code-point sequences under the selected standard. It is not spellcheck, grammar correction, smart punctuation, transliteration, case folding, quote conversion, dash substitution, whitespace rewriting, censorship, or editorial judgment.

The pipeline must explicitly handle:

- an initial byte-order mark or embedded BOM-like character;
- invalid UTF-8 byte sequences at byte-oriented boundaries;
- null characters;
- carriage return, line feed, and combined line endings;
- unsupported C0/C1 and other control characters;
- tabs and other spacing characters under later policy;
- zero-width and format characters;
- variation selectors and emoji sequences;
- combining marks and canonically equivalent sequences;
- lone or malformed surrogate data received through an interface that can represent it;
- bidirectional embedding, override, isolate, and mark characters; and
- Unicode version changes affecting normalization or security guidance.

Dangerous bidirectional controls may be rejected, surfaced for explicit review, or allowed only under a documented rule that protects legitimate multilingual writing. The system must not silently delete or reorder them, because doing so could corrupt legitimate text or conceal a mismatch between display and storage.

Normalization is deterministic and versioned. The same accepted input and normalization version produces the same authoritative content. If a future Unicode or application rule would materially change stored content, existing revisions retain their declared interpretation or undergo an explicit representation migration; they are never silently reinterpreted on read.

## Validation and Content Limits

The server validates request size before expensive decoding, normalization, parsing, comparison, indexing, AI preparation, or export work. It then validates decoded content, declared format version, supported characters, normalization result, and documented content limits.

Limits must protect:

- HTTP and application memory;
- Django request processing;
- PostgreSQL transactions and storage;
- revision comparison and conflict recovery;
- browser rendering and editor responsiveness;
- search indexing and excerpt generation;
- AI context construction;
- exports and conversions;
- backups and restoration; and
- abuse and denial-of-service boundaries.

Limits are based on explicit byte, character, line, paragraph, or other measured constraints where justified, not an assumption that every Scene is short. The exact thresholds and whether every dimension needs an independent limit remain later policy decisions.

Rejected content remains in the browser draft or protected temporary conflict/draft storage according to later policy. The response identifies a safe actionable category and relevant limit without echoing manuscript text into logs, telemetry, URLs, metrics, or error bodies beyond the authorized response needed to recover.

Validation failures do not partially normalize and save content, advance the Scene version, create a revision, update derived indexes, submit AI work, or trigger exports. Client-side checks may improve usability but never replace server validation.

## Whitespace and Creative Fidelity

Author-intended whitespace, paragraph breaks, and punctuation are part of the authoritative text. Representation normalization must preserve them except for the explicitly documented canonical line-ending conversion and any later narrowly approved character rule.

The system must not silently:

- trim leading or trailing spaces across the whole document;
- remove final line breaks merely as a style preference;
- collapse repeated spaces or blank lines;
- convert tabs to spaces or spaces to tabs without a declared rule;
- rewrap or join paragraphs;
- change quotation marks, apostrophes, ellipses, hyphens, or dashes;
- alter capitalization;
- autocorrect words;
- apply typographic substitutions;
- strip literal Markdown or tag-looking text; or
- normalize creative spelling, dialect, invented language, or character voice.

If the editor offers spellcheck, smart punctuation, auto-capitalization, or similar assistance, it must be visible browser/editor behavior whose proposed text is reviewable before save. The server normalization layer does not perform those changes.

Whitespace display may be derived for presentation, including CSS wrapping, indentation visualization, or paragraph spacing. Display changes do not rewrite authoritative content.

## Editor Boundary

Version 1 may begin with a server-rendered textarea or a progressively enhanced plain-text editor. This ADR selects neither an editor package nor a frontend framework.

The editor receives:

- the authorized Scene and current Scene Revision identity;
- the authoritative committed plain-text content;
- content-format and normalization version information needed for safe submission;
- the accepted Scene integer version/current-revision concurrency token; and
- bounded metadata needed for the editing view.

The editor produces proposed complete plain text. Browser DOM, contenteditable structure, component state, editor-native nodes, decorations, syntax highlighting, hidden elements, spellcheck annotations, and accessibility scaffolding are not authoritative.

Clipboard, paste, drag-and-drop, IME composition, dead keys, mobile or desktop input methods, undo/redo, spellcheck, screen readers, keyboard-only use, zoom, high contrast, and supported browser behavior require testing. Pasted HTML is converted to plain text through an explicit deterministic rule rather than trusted as markup. The rule must cover line breaks, lists, tables, images, links, hidden content, scripts, styles, and unsupported embedded objects without silently creating authority.

The editor must communicate unsaved, saving, saved, failed, offline, and conflicted states honestly. It may display saved only after the server acknowledges the committed revision and returns the new token. Optimistic UI may indicate pending work but cannot claim durability before acknowledgment.

A server-rendered textarea is the lowest-complexity candidate. Progressive enhancement may add draft recovery, shortcuts, counts, conflict comparison, and accessibility improvements without changing the persistence contract.

## Browser Drafts and Local Persistence

Text currently present in the editor but not acknowledged by the server is a browser draft. It may be newer than the server and valuable to the author, but it is not authoritative merely because it is newer.

Browser drafts, autosave buffers, undo stacks, cursor position, selection, scroll position, composition state, spellcheck state, editor preferences, find state, and layout state are not committed Scene Revision content.

If browser local storage is later used, it is a recovery convenience only. Its technology, encryption behavior, quota, eviction, expiry, multi-tab coordination, privacy notice, cleanup, device exposure, and association with account/Workspace/Scene/revision require a later UX and security policy. Local data cannot bypass authentication or become readable across unauthorized sessions.

The browser must never become the sole copy of acknowledged content. Server acknowledgment means the authoritative revision exists in PostgreSQL under the accepted transaction, not merely that a local draft was cached.

Navigation away with unsaved content should warn or preserve a bounded draft according to later UX policy. Browser crash, storage eviction, extension access, device backup, shared profiles, and private-browsing behavior remain client-environment risks and must be communicated honestly.

An autosave request is a proposed server save triggered by policy. Local draft persistence is storage on the client without an authoritative commit. They must not share a misleading saved indicator. Exact autosave cadence, trigger, debounce, focus behavior, offline behavior, and whether Version 1 uses autosave remain undecided.

## Save and Revision Transaction

A save submits the complete proposed content, declared supported format version, and accepted concurrency token containing the observed Scene integer version and current-revision ID or permitted null state. No patch, operational transform, browser diff, DOM mutation list, or editor-native transaction is authoritative in Version 1.

Before committing, Django application services:

1. validate request size before expensive processing;
2. authenticate or recheck current session state as required;
3. validate CSRF for cookie-authenticated state-changing requests;
4. authorize the actor, Workspace, Scene, lifecycle, and save operation;
5. decode and validate content and format metadata;
6. apply only the documented deterministic normalization version;
7. enforce content limits;
8. revalidate the Scene's current version and revision inside the accepted transaction;
9. apply accepted idempotency handling for ambiguous retries; and
10. create the immutable revision and advance the Scene pointer/version atomically.

The Scene Revision stores the complete normalized content plus format and normalization metadata, stable revision ID, Scene and Workspace identity, lineage, provenance, timestamps, and other fields required by ADR-0004. Revision content is distinct from provenance and security audit records.

On success, the server returns the new revision identity and concurrency token. Only then may the editor show saved. Derived work may occur transactionally where required for correctness or asynchronously where rebuildability and consistency are explicit, but its failure cannot make a nonexistent revision appear committed.

A validation, authorization, CSRF, concurrency, storage, transaction, or normalization failure creates no authoritative revision and does not advance the current pointer. Network retries follow ADR-0004 idempotency rules and never blindly duplicate durable effects.

## Empty Scene Semantics

Empty plain text is a valid representable content value, distinct from missing content, a missing request field, invalid decoding, and a Scene with no committed revision.

The later physical schema/editor decision must choose one explicit initial-state model:

- a newly created Scene has no current revision until its first acknowledged save, and saving empty text creates an explicit first revision; or
- creation includes an explicit initial empty revision through the ordinary authoritative transaction.

If both an empty saved Scene and a never-committed Scene exist, APIs, editor state, export, comparison, backup, restoration, and tests must preserve the distinction. The system must not infer absence from a falsey string or silently skip an intentional empty save.

Whitespace-only content is not automatically empty. Any warning or policy concerning it must not trim or transform it silently. Exact initial-state behavior remains undecided, consistent with ADR-0004.

## Conflict Content Boundary

A stale save does not overwrite current content and does not automatically create a committed branch or Scene Revision. The current authoritative revision remains selected by the Scene pointer.

The rejected submitted content is sensitive draft material preserved long enough for the authorized owner to compare, copy, retry deliberately, or abandon it. It is distinct from:

- the base revision the editor observed;
- the current authoritative revision;
- an immutable committed revision;
- browser-local draft state;
- revision lineage;
- provenance and audit; and
- an automatically merged result, which Version 1 does not create.

Conflict storage, whether server-side or browser-assisted, has bounded retention, Workspace authorization, privacy protection, cleanup, and clear status. It does not enter search, backlinks, normal AI context, exports, or backups unless a later explicit policy requires protected inclusion.

Resolving a conflict submits a complete deliberate proposal against the newest accepted token and follows ordinary validation, normalization, authorization, transaction, provenance, and idempotency rules. Editor comparison or copy tools do not confer authority.

## Derived Rendering

HTML presentation is derived from authoritative plain text and is rebuildable. The default rendering escapes manuscript characters before adding application-controlled structure for paragraphs and line breaks.

Manuscript text is never trusted as HTML, CSS, a URL, template source, script, event-handler content, or browser directive. Tag-looking text remains visible text. If a later feature deliberately interprets Markdown or another syntax, it must define a separate derived rendering boundary, escaping/sanitization strategy, feature set, and tests without changing authority.

Derived HTML must be escaped or sanitized according to its generation path. Output escaping, contextual encoding, a restrictive Content Security Policy, safe link policy, and sanitization where actual markup is introduced are defense in depth. Sanitization does not convert hostile markup into authoritative content.

Rendering caches may be discarded and rebuilt from the source revision. If retained, they record the source revision identity and renderer version sufficient to detect staleness. They never become the only copy of content or a restoration source in place of the authoritative revision.

## Search, Excerpts, and Counts

Word counts, character counts, line counts, paragraph counts, excerpts, previews, search text, search vectors, highlights, and comparison views are derived from authoritative normalized content under documented algorithms.

These values may differ across languages, Unicode segmentation rules, renderer versions, or search configurations. They are conveniences and indexes, not creative content or revision identity. Their algorithms and versions should be documented where stable output matters.

Retained derived data records or resolves its source Scene Revision identity. A pointer change invalidates or supersedes current-only projections. Historical projections may be regenerated from immutable revisions.

Search indexes and caches may be discarded and rebuilt. Search results remain authenticated, Workspace-scoped, state-aware where applicable, and unable to reveal unauthorized record existence. Search terms, excerpts, and manuscript bodies stay out of routine logs and telemetry.

An excerpt is a bounded projection, not a replacement for the complete revision. Truncation must respect Unicode boundaries and avoid generating misleading or unsafe markup.

## AI Context Projection

AI review receives only explicitly selected, bounded context derived from committed authoritative revisions or, when a feature explicitly permits it, an explicitly authorized submitted draft. It never receives an entire Workspace merely because text storage is simple.

The context manifest includes the source Scene Revision ID where committed content is used, content-format and normalization version, bounded source references, relevant state/provenance, selection rules, limits, and integrity information required by the AI-context architecture.

Hidden editor state, browser DOM, editor-native JSON, local undo history, unrelated drafts, rejected conflicts, comments, clipboard content, selection, cursor position, spellcheck data, browser storage, and extension state are excluded unless a future approved feature explicitly selects and explains them.

AI context may normalize transport framing or select bounded excerpts, but it does not silently rewrite the authoritative revision. The provider receives no HTML or markup authority and no direct database, editor, filesystem, search, export, backup, or Workspace access.

Provider output remains AI suggestion data. Applying it is an explicit owner action that submits a complete proposed value through ordinary authentication, authorization, CSRF, content validation, normalization, concurrency, idempotency, revision, and provenance rules. Representation normalization cannot be used as a reason for autonomous AI rewriting.

## Export Formats

Author-facing plain-text export preserves the exact authoritative content value under a documented UTF-8 encoding and line-ending rule. If external line endings differ from the canonical internal convention, the export declares the conversion and supports deterministic round trip.

Structured archive export preserves:

- Workspace, Scene, and Scene Revision stable IDs;
- revision lineage and current pointer;
- Scene integer version;
- exact authoritative content;
- content-format and normalization versions;
- line-ending semantics;
- provenance and lifecycle metadata required for meaning;
- integrity metadata; and
- archive/format version and compatibility information.

Markdown, HTML, DOCX, PDF, and other formats are derived exports. They may add presentation or lose information not expressible in their target model. A file extension or renderer does not change the authoritative representation.

Exports are private, authenticated, authorized, recently authenticated where required by ADR-0005, protected from public URLs, and excluded from routine logs. Export is not backup: an author-facing subset may omit operational state, history, authentication state, private objects, or restoration metadata.

No exact export library, archive format, filename policy, line-ending choice, or rich presentation is selected here.

## Import Transformation

Import treats every external source as untrusted. External plain text, Markdown, HTML, DOCX, old Story Engine exports, provider documents, and other formats pass through an explicit staged transformation into Version 1 normalized plain text.

The import workflow records source type, source identity where available, decoder/parser and transformation version, warnings, discarded or unsupported features, assigned Strange Novelty IDs, content-format version, and author disposition.

Embedded HTML, scripts, styles, macros, comments, tracked changes, hidden text, metadata, images, links, formulas, active content, and external references are not automatically trusted or promoted into Scene content. The author previews material and warnings before an authorized apply operation.

Markdown import does not silently make Markdown authoritative. It either preserves literal syntax as plain text or performs a separately defined visible transformation to plain text. HTML and rich documents require deterministic text extraction rules with parser isolation, limits, and security review.

Imported material remains Imported content until explicit author review. Applying an import creates ordinary Scene revisions through the accepted transaction and cannot overwrite current content without current concurrency authorization.

## Backup and Restoration

Backup is broader than content export. It preserves the database state and required private objects, revision graph, current pointers, identities, provenance, lifecycle state, integrity evidence, and operational information required for complete recovery under the backup architecture.

Backups contain private manuscript content and receive equivalent confidentiality and integrity protection. They exclude live credentials and sessions where required by ADR-0005 or restore them only through an explicitly safe invalidation/reconciliation process.

Restoration of the same archive preserves each authoritative revision's exact content and its content-format and normalization metadata. Restoration does not renormalize old revisions under the current rule, rerender and store HTML as source, collapse history, infer current revision from timestamps, or regenerate identities.

Before activation, restoration verifies encoding, declared representation versions, content integrity, revision/Scene/Workspace relationships, lineage, current pointers, limits, and compatibility. Derived HTML, excerpts, counts, search indexes, and AI projections may be discarded and rebuilt from authoritative revisions.

Restored content remains private and untrusted until validation completes in an isolated or deliberately prepared target. A successful database restore is not sufficient until authenticated application checks confirm exact representative content, line breaks, identities, revisions, search rebuild, export round trip, and editor behavior.

## Representation Migration

Representation migration is a deliberate transformation of stored authoritative content or its interpretation. It is not an ordinary edit, editor upgrade, renderer change, library update, or browser normalization side effect.

Future rich text, structured documents, Markdown authority, or a new Unicode/normalization policy requires a later ADR that defines:

- the new stable format and version;
- deterministic transformation and loss reporting;
- whether old revisions remain in their original format or receive new migrated representations;
- preservation of Scene and Scene Revision identity;
- lineage and current-pointer behavior;
- comparison across formats;
- export and import compatibility;
- AI context behavior;
- rollback and recovery;
- backup/restoration of mixed versions; and
- representative fidelity and security tests.

Existing immutable revision content must not be silently rewritten in place. If migration creates new authoritative representations, their relationship to original content and IDs must be explicit. The author must be able to export and restore every retained revision without depending on the retired editor.

Changing an editor package while retaining the same plain-text contract is not necessarily a representation migration, but it still requires paste, IME, whitespace, accessibility, draft, save, conflict, and round-trip tests.

## Django and PostgreSQL Boundary

Django application services own decoding, validation, normalization-version selection, content limits, authentication/session rechecks, authorization, Workspace scoping, CSRF, concurrency, idempotency, transaction orchestration, provenance, and safe response behavior.

PostgreSQL stores the authoritative normalized text and representation metadata in the later physical schema. A PostgreSQL text-compatible type is expected, but exact columns, constraints, indexes, storage parameters, collations, full-text configuration, generated columns, and derived tables remain undecided.

Database encoding and collation support correct storage and querying but do not replace the application content-format contract. Collation, case folding, search dictionaries, or index normalization must not mutate stored revision content.

Constraints and transactions reinforce format-version validity, identity, lineage, and atomic pointer advancement. Database triggers or generated fields must not perform undocumented creative rewriting or become the only normalization implementation.

Complete Django models, forms, views, templates, JavaScript, APIs, PostgreSQL objects, migrations, editor integration, and storage schema are outside this ADR.

## Rationale

Normalized UTF-8 plain text is the smallest durable representation that satisfies Version 1 writing, revision, search, AI, export, backup, and restoration needs without allowing an editor package or markup language to define creative truth.

It preserves prose and paragraph structure directly, is inspectable and portable, has broad platform and database support, and makes full-snapshot revisions independently readable. It reduces XSS and parser surface because manuscript text is never authoritative markup.

One authoritative form avoids divergence between Markdown and HTML or between editor-native JSON and derived text. Explicit format and normalization versions prevent library upgrades from silently changing old revisions.

Complete-content saves align with ADR-0004's snapshot and concurrency model. The server can validate one proposal, compare one accepted token, and atomically create one immutable revision without trusting browser diffs.

Derived projections let search, counts, HTML, AI context, and exports evolve independently while remaining reproducible from revision identity. Future rich text remains possible through an explicit migration instead of being embedded prematurely in Version 1.

## Decision Criteria

Representations and editor boundaries are evaluated against:

1. creative fidelity for prose, whitespace, punctuation, and multilingual Unicode;
2. independence from an editor, browser DOM, frontend framework, or provider;
3. simple immutable full snapshots and exact revision retrieval;
4. deterministic normalization and stable interpretation over time;
5. XSS, injection, parsing, and content-security risk;
6. server-side validation, concurrency, idempotency, and atomic save behavior;
7. search, excerpt, comparison, AI-context, and rendering derivation;
8. human-readable and structured export portability;
9. import transformation and provenance clarity;
10. backup, restoration, integrity verification, and representation migration;
11. accessibility, IME, clipboard, and browser interoperability;
12. maintainability for one owner and a narrow Version 1; and
13. ability to add richer representation later without losing identity or history.

## Alternatives Considered

### Plain UTF-8 text

Selected. It is portable, inspectable, editor-independent, straightforward to validate, safe to escape, and sufficient for Version 1 prose and paragraph structure. It cannot represent authoritative emphasis, headings, comments, embeds, tables, or other rich structure.

### Markdown as the authoritative source

Markdown is portable and readable and can express lightweight formatting. It is not selected because dialects, extensions, parser changes, embedded HTML, escaping, and author intent around literal punctuation introduce interpretation ambiguity. Markdown typed in Version 1 remains literal text.

### Sanitized HTML as the authoritative source

HTML can preserve rich presentation and is broadly renderable. It is rejected as authority because sanitization policies evolve, equivalent DOMs serialize differently, active-content risk is high, editor/browser output is unstable, and plain-text/search/export meaning becomes parser-dependent.

### Structured JSON document model

A product-owned schema could represent paragraphs, emphasis, annotations, links, and future extensions explicitly. It offers stronger rich-text semantics than HTML but requires a schema, migration strategy, editor mapping, canonical serialization, validation, accessibility, comparison, export, and recovery design beyond Version 1 needs. Deferred.

### Rich-text editor native JSON

Native JSON can integrate closely with a selected editor. It is rejected as the durable contract because package versions, plugins, node schemas, normalization rules, and transaction semantics would couple every revision and migration to one editor ecosystem.

### Dual authoritative Markdown and HTML

Rejected. Two authoritative forms can diverge, require conflict resolution and canonical direction, complicate hashing and revisions, and make restoration ambiguous. HTML should be derived from one source.

### Binary or proprietary editor formats

Rejected because they reduce inspectability, portability, diffability, recovery independence, and exit options and may require unavailable proprietary software.

### Plain text for Version 1 with later migration

Selected. The later migration is not assumed free: a future ADR must preserve every old revision and explicitly report any transformation or loss.

### Structured document model with derived plain text and HTML

This is the strongest future-rich-text alternative. One structured source could derive search, AI text, and rendering consistently. It is deferred because Version 1 has no approved rich-text requirements or schema, and its canonicalization and migration burden would delay the core writing workflow.

### Defer content representation until editor implementation

Rejected. It would let an editor package, browser behavior, or prototype become the accidental persistence contract and block reliable revision, export, AI-context, and restoration design.

### Server-rendered textarea or plain-text editor

Strong Version 1 starting point. It naturally edits the selected representation, minimizes dependencies and DOM transformation, and supports conventional forms. It still requires careful draft, IME, paste, accessibility, conflict, and large-content testing.

### Progressively enhanced textarea

Preferred conceptual direction without selecting a package. Enhancement can add counts, shortcuts, draft recovery, status, and comparison while retaining a standard plain-text form and server boundary.

### Markdown editor

Possible as a plain-text editing aid, but syntax highlighting or preview must not imply that Markdown semantics are authoritative. A dedicated Markdown editor may mislead users about the selected contract and is not selected here.

### Structured rich-text editor

Deferred. Mapping rich DOM/JSON state into plain text could discard author-visible formatting, while storing native state would contradict this decision. It becomes appropriate only with a later rich-text representation ADR.

### Custom contenteditable editor

Rejected for Version 1. Browser normalization, selection, IME, paste, undo, accessibility, security, and serialization behavior make a custom implementation disproportionately risky.

### Desktop-native editor integration

Not selected. It reintroduces local trust, synchronization, path, credential, conflict, and portability questions and is outside the private web Version 1 boundary.

### External document provider as primary editor

Rejected. It would make an integration a practical custodian of current creative state, complicate authentication, offline behavior, provenance, conflict, export, privacy, and provider loss. Future integration may import or synchronize through a separate ADR without becoming authoritative by default.

### Browser-only local-first editor

Rejected as the sole persistence model. It can provide excellent offline responsiveness but would make browser storage authoritative, complicate multi-device conflict, backup, server authorization, and recovery, and contradict the accepted server boundary. Bounded local draft recovery remains possible.

## Comparative Assessment

### Representation comparison

| Representation | Fidelity in V1 | Portability | Security/parser surface | Editor coupling | Decision |
| --- | --- | --- | --- | --- | --- |
| UTF-8 plain text | Prose, whitespace, line breaks | Strong | Lowest | Low | Selected |
| Markdown source | Lightweight markup | Strong but dialect-sensitive | Moderate | Low/moderate | Not selected |
| Sanitized HTML | Rich presentation | Moderate | High | Browser/editor-sensitive | Rejected |
| Product JSON model | Potentially rich/precise | Strong if documented | Moderate | Product schema | Deferred |
| Editor-native JSON | Rich | Package-dependent | Moderate | High | Rejected as authority |
| Markdown + HTML authority | Rich | Ambiguous | High | Moderate | Rejected |
| Binary/proprietary | Potentially rich | Weak | Opaque | Very high | Rejected |
| Plain text then migrate | Sufficient V1 | Strong | Low | Low | Selected strategy |
| Structured source + projections | Strong future model | Potentially strong | Moderate | Moderate | Deferred |
| Defer choice | Unknown | Unknown | Unknown | Accidental | Rejected |

### Editor comparison

| Editor approach | Matches plain-text authority | Complexity | Offline/local risk | Decision |
| --- | --- | --- | --- | --- |
| Server-rendered textarea | Direct | Lowest | Bounded draft only | Strong starting point |
| Progressively enhanced textarea | Direct | Low/moderate | Must remain non-authoritative | Preferred concept |
| Markdown editor | Direct text, implied semantics risk | Moderate | Bounded | Possible aid, not selected |
| Structured rich-text editor | Lossy mapping to plain text | High | Complex | Deferred |
| Custom contenteditable | Unstable serialization | Very high | Complex | Rejected V1 |
| Desktop-native integration | Requires synchronization | High | Broad local trust | Not selected |
| External provider | Provider-dependent | High | Remote authority risk | Rejected primary |
| Browser-only local-first | Direct but client-authoritative | High | Core authority conflict | Rejected sole model |

### Persistence-boundary comparison

| Approach | Server authority | Conflict clarity | Restoration | Decision |
| --- | --- | --- | --- | --- |
| Complete text + accepted token | Strong | Explicit | Independent snapshots | Selected |
| Browser patch/diff authority | Weaker | Patch-base sensitive | Reconstruction risk | Rejected V1 |
| Editor operation log | Package/protocol-dependent | Branch/merge complexity | Replay-dependent | Rejected V1 |
| Dual server/client authority | Ambiguous | Complex reconciliation | Ambiguous | Rejected |
| Provider document authority | External | Provider semantics | Provider-dependent | Rejected |

## Evidence

### Repository evidence

- Product vision and principles prioritize authorial control, meaningful distinctions, privacy, portability, backup, restoration, and a narrow first release.
- Version 1 scope requires dependable Scene drafting and revision without replacing a full word processor.
- The roadmap requires the private, recoverable writing workflow before broader integrations or rich capabilities.
- Architecture documents keep the browser untrusted, authoritative storage server-side, derived indexes rebuildable, AI context bounded, and integrations non-authoritative.
- The data model separates Scene identity, immutable Scene Revision content, metadata, provenance, and lifecycle.
- The security architecture prohibits manuscript content in routine logs and requires escaping, sanitization, CSP, input limits, authorization, protected exports, and isolated restoration.
- ADR-0001 through ADR-0005 establish Django mediation, PostgreSQL authority, full snapshots, optimistic concurrency, conflict recovery, idempotency, authenticated Workspace scoping, CSRF, and bounded administrative/service authority.
- The old Story Engine audit values focused editing, word counts, snapshots, and readable exports but rejects browser-side database authority, selective history, incomplete export/recovery, and broad webview trust.

### Official guidance reviewed conceptually

The decision is informed conceptually by current official and standards material without binding to a particular version or package:

- [Unicode Normalization Forms](https://www.unicode.org/reports/tr15/)
- [Unicode Security Considerations](https://www.unicode.org/reports/tr36/)
- [Unicode Bidirectional Algorithm](https://www.unicode.org/reports/tr9/)
- [Django request and response documentation](https://docs.djangoproject.com/en/stable/ref/request-response/)
- [Django forms documentation](https://docs.djangoproject.com/en/stable/topics/forms/)
- [Django templates](https://docs.djangoproject.com/en/stable/topics/templates/)
- [Django security documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [Django model field reference](https://docs.djangoproject.com/en/stable/ref/models/fields/)
- [PostgreSQL character-set support](https://www.postgresql.org/docs/current/multibyte.html)
- [PostgreSQL character types](https://www.postgresql.org/docs/current/datatype-character.html)
- [HTML textarea element](https://html.spec.whatwg.org/multipage/form-elements.html#the-textarea-element)
- [Clipboard API and events](https://www.w3.org/TR/clipboard-apis/)
- [Input Events](https://www.w3.org/TR/input-events-2/)
- [Web Content Accessibility Guidelines](https://www.w3.org/TR/WCAG22/)
- [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html)
- [OWASP Cross Site Scripting Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [OWASP Content Security Policy Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)

This guidance supports explicit Unicode normalization policy, contextual output encoding, allowlist-oriented validation, safe handling of untrusted markup, request limits, deterministic form processing, accessibility testing, and CSP as defense in depth rather than a substitute for escaping.

### Evidence still required

Before acceptance or implementation:

- test candidate Unicode normalization forms with representative synthetic multilingual and creative text;
- decide canonical internal and export line endings;
- define BOM, null, control, tab, zero-width, variation-selector, surrogate, and bidirectional-control policy;
- measure representative synthetic Scene sizes and operations without inspecting private manuscripts;
- define byte, character, line, paragraph, and request limits;
- test textarea and progressive-enhancement behavior across supported browsers;
- test IME, composition, dead keys, clipboard, paste, drag/drop, undo, spellcheck, screen readers, keyboard navigation, zoom, and high contrast;
- define deterministic HTML-to-plain-text paste/import behavior;
- test normalization idempotence and stable hashes across supported runtime versions;
- test complete-content saves, retries, failures, conflicts, empty content, whitespace-only content, and multi-tab editing;
- define browser-draft retention and privacy policy if local persistence is used;
- define renderer escaping, line-break behavior, CSP, cache invalidation, and source-revision linkage;
- define count, excerpt, comparison, and search segmentation algorithms;
- verify AI context manifests carry revision and format identity and exclude hidden editor state;
- specify plain-text and structured-archive round trips;
- test hostile HTML/Markdown/rich-document imports and transformation warnings;
- test exact restoration of representative Unicode, whitespace, line endings, IDs, lineage, and format metadata; and
- prototype a future-format migration using synthetic data to verify the chosen versioning boundary.

## Consequences

### Positive

- Authoritative Scene content is simple, portable, inspectable, and independent of editor packages.
- Full snapshots remain independently readable and recoverable.
- One source prevents Markdown/HTML/editor-state divergence.
- Plain text substantially reduces active-markup and parser attack surface.
- Explicit normalization versions preserve stable interpretation over time.
- Complete-content saves align directly with accepted concurrency and idempotency rules.
- Rendering, search, counts, AI context, and exports can evolve as rebuildable projections.
- Exports can preserve exact text without proprietary tooling.
- Restoration can verify exact content and discard stale derived data.
- Future rich text remains possible through an explicit, testable migration.

### Negative

- Version 1 cannot authoritatively represent emphasis, headings, semantic links, comments, footnotes, tables, embeds, or rich layout inside Scene content.
- Plain-text rendering may feel less polished than a rich editor.
- Literal Markdown may create user-expectation ambiguity if previews are later added.
- Unicode and whitespace fidelity still require careful cross-browser and cross-runtime testing.
- Complete snapshots duplicate full text on every committed save.
- Complete-content requests can be larger than patches and require explicit limits.
- Browser-local draft recovery remains a separate sensitive-data feature.
- Derived counts, excerpts, search, and export renderings need versioning or rebuild logic.
- Import from rich formats necessarily loses or externalizes formatting and embedded features.
- Later rich-text migration will require substantial compatibility and fidelity work.

### Neutral or Operational

- PostgreSQL text storage does not itself define the content contract.
- A textarea can be replaced without migrating content if the plain-text contract remains stable.
- Browser spellcheck and smart punctuation are client behavior, not normalization.
- HTML, Markdown, DOCX, and PDF remain useful outputs even though they are not authoritative.
- Empty Scene initial semantics remain a later schema/editor choice.
- Autosave may be added later without changing what constitutes an acknowledged revision.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Normalization changes creative text | Loss of author fidelity | Narrow documented rules, representative tests, versioning, no editorial transformations | Unicode equivalence can still surprise users |
| Unicode version/library changes output | Old revisions reinterpret differently | Store versions, test runtime upgrades, never normalize silently on read | Some ecosystem rendering changes remain |
| Bidi controls conceal displayed meaning | Spoofing or review confusion | Explicit policy, visible review/rejection where appropriate, security testing | Legitimate multilingual needs complicate policy |
| Browser normalizes pasted/input text | Unexpected saved content | Test IME/clipboard/browser behavior, show proposed text, server deterministic rules | Platform behavior varies |
| Pasted HTML introduces active content | XSS or hidden text | Deterministic plain-text conversion, escape rendering, CSP, hostile tests | Conversion may lose intended structure |
| Plain text is too limited | Author frustration or workarounds | Narrow V1, honest UI, derived exports, later structured-format ADR | Rich requirements may emerge early |
| Literal Markdown is mistaken for formatting | Expectation mismatch | Label plain-text authority, keep previews explicitly derived | Users may still infer semantics |
| Complete-content saves are large | Latency or resource exhaustion | Early request limits, representative tests, bounded Scenes | Very large Scenes remain costly |
| Derived data becomes stale | Wrong counts/search/previews | Source revision IDs, invalidation, rebuildability, consistency tests | Asynchronous lag may remain visible |
| Renderer trusts manuscript markup | Script execution or injection | Contextual escaping, controlled structure, sanitization where markup exists, CSP | XSS elsewhere in application remains possible |
| Local drafts leak manuscripts | Device/browser exposure | Optional bounded policy, authorization binding, expiry, disclosure, cleanup | Browser extensions and OS access remain |
| Saved indicator precedes commit | False durability and data loss | Show saved only after server acknowledgment and new token | Network ambiguity still needs careful UX |
| Conflict draft becomes authority accidentally | History corruption | Separate storage/status, ordinary resubmission, no auto branch/merge | Retention and UX errors remain possible |
| AI receives hidden/editor data | Privacy and scope violation | Build context from authorized revision projection and manifest only | Implementation regressions remain possible |
| Rich import silently loses data | Creative loss | Staged preview, warnings, provenance, explicit transformation | Some formatting cannot map to plain text |
| Export line-ending conversion breaks round trip | Text mismatch | Declare rules, structured archive preserves semantics, round-trip tests | External tools may rewrite files |
| Restoration renormalizes history | Immutable revision corruption | Preserve exact bytes/logical content and versions, verify hashes | Bad legacy metadata may need repair |
| Future migration rewrites revisions in place | Lost provenance/history | Later ADR, immutable originals, transformation reports, rollback tests | Mixed formats add operational complexity |
| Manuscript enters logs/errors | Privacy breach | Allowlisted telemetry, safe error categories, no content echo | Debug tooling can regress |

## Security and Privacy Review

- Security-sensitive: Yes; Scene content is private manuscript data and crosses browser, server, database, rendering, AI, export, and restoration boundaries.
- Primary references: `docs/architecture/security.md`, `docs/architecture/data-model.md`, `docs/architecture/ai-context.md`, ADR-0001, ADR-0002, ADR-0003, ADR-0004, and ADR-0005.
- Additional references: product vision, principles, scope, roadmap, integrations, and the old Story Engine audit.

### Assets and trust boundaries

Protected assets include committed Scene content, revisions, browser drafts, rejected conflict content, derived excerpts, search indexes, AI context, imports, exports, backups, and restored archives. The browser, clipboard, DOM, local storage, extensions, operating-system input/spellcheck services, imported documents, renderer output, providers, and restored artifacts cross trust boundaries.

### Rendering and injection

Manuscript text is untrusted for rendering even when written by the owner. It is escaped as text. Any application-generated markup uses contextual encoding, controlled URL handling, sanitization where appropriate, and CSP defense in depth. HTML-like text, Markdown, bidirectional controls, and Unicode confusables cannot create domain authority.

### Privacy

Manuscript content does not enter routine logs, traces, analytics, exception bodies, URLs, query strings, metrics labels, security events, or client-visible configuration. Temporary draft and conflict storage inherits manuscript sensitivity, Workspace authorization, retention, backup, deletion, and incident-response requirements.

Browser spellcheck, extensions, accessibility tools, clipboard managers, OS services, and synchronized browser profiles are outside the server trust boundary and may observe editor text. Supported deployment/user guidance should disclose material client-environment risks without claiming the server can control them.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- invalid bytes, BOMs, nulls, controls, bidirectional text, combining sequences, emoji, and normalization idempotence;
- preservation of spaces, blank lines, tabs under policy, punctuation, final line breaks, and multilingual text;
- request and content limits before expensive processing;
- HTML/script/URL-looking text rendered inert;
- textarea and enhanced editor paste, IME, undo, accessibility, offline, and navigation behavior;
- saved-state accuracy under success, validation error, timeout, disconnect, ambiguous response, and retry;
- authentication, Workspace authorization, CSRF, concurrency, atomic rollback, and idempotency;
- empty, whitespace-only, first-save, stale-save, and conflict-recovery behavior;
- derived cache/index source-revision linkage and rebuild;
- search and excerpt authorization and privacy-conscious logging;
- AI manifest exactness and exclusion of DOM/local/hidden state;
- plain-text and structured archive round trips;
- hostile import parsing and visible loss warnings;
- backup confidentiality and exact isolated restoration; and
- absence of manuscripts from logs, telemetry, URLs, errors, security events, and provider metadata.

### Residual risk

The browser, application server, database, search system, export process, backup process, and authorized AI gateway necessarily process plaintext manuscript content. A compromised endpoint or server can expose it. Unicode display differences, browser input behavior, owner-device services, and later conversion tools can alter or reveal text despite a stable server representation.

## Product and Architecture Alignment

### Product alignment

The decision protects authorial control and creative fidelity, keeps revisions understandable and recoverable, makes AI scope explicit, preserves useful exports, and avoids locking the archive to an editor or provider.

### Scope alignment

Plain text supports the required Version 1 Scene drafting and revision workflow without claiming to replace a full word processor. It leaves rich text, external document editing, and advanced publishing outside the first release.

### ADR alignment

- ADR-0001: the browser proposes content; Django services authorize and persist it.
- ADR-0002: Django owns validation, normalization, rendering boundaries, and save orchestration.
- ADR-0003: PostgreSQL stores authoritative revisions and derived indexes remain rebuildable.
- ADR-0004: full snapshots, stable revision IDs, optimistic concurrency, conflict handling, idempotency, and atomic pointer advancement are preserved.
- ADR-0005: every save, draft-recovery read, search, AI operation, export, import, backup, and restoration remains authenticated, Workspace-scoped, and protected by applicable CSRF and recent-authentication rules.

### Architecture alignment

The decision separates content from metadata and provenance, keeps derived views rebuildable, makes AI context narrow, treats imports as untrusted, distinguishes export from backup, and preserves exact content through isolated restoration.

### Normative-document impact

If accepted, the data-model, security, AI-context, export, import, backup, and restoration documentation should be reconciled with the selected content-format and editor boundary, and the ADR index should be updated. No normative document is changed by this Proposed ADR.

## Migration and Portability

UTF-8 plain text and explicit representation versions are portable across supported browsers, Django releases, PostgreSQL versions, editor packages, operating systems, and export tools when line-ending and normalization rules are honored.

Migration between databases or frameworks preserves the exact authoritative content value, format version, normalization version, stable IDs, lineage, current pointer, and provenance. Database dump encoding, client encoding, collation, and transfer tools must be verified not to reinterpret text.

Old Story Engine chapters, snapshots, HTML exports, plain-text exports, or structured exports are untrusted migration inputs. They pass through staged transformation, receive new Strange Novelty identity mappings as required by ADR-0004, remain Imported content, and do not inherit old editor or markup authority.

External document providers may later exchange derived documents or staged imports, but their document model does not become authoritative without a separate integration and representation decision.

Future representation changes preserve original revision identity and content interpretation or explicitly create versioned migrated representations with traceable relationships. Exit exports remain possible without the editor that created them.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Define the stable Version 1 content-format name and version.
- [ ] Test and select one Unicode normalization form.
- [ ] Define canonical internal and author-facing plain-text export line endings.
- [ ] Define BOM, null, control, tab, zero-width, variation-selector, surrogate, and bidirectional-control rules.
- [ ] Define deterministic normalization order and version metadata.
- [ ] Measure representative synthetic Scene sizes and set request/content limits.
- [ ] Decide the initial empty-Scene/current-revision semantics.
- [ ] Define the physical Scene Revision content and metadata schema in a later schema decision.
- [ ] Select an editor approach and supported browser matrix without changing the persistence contract.
- [ ] Test textarea/progressive enhancement, IME, clipboard, paste, drag/drop, undo, spellcheck, and accessibility.
- [ ] Define deterministic pasted-HTML-to-plain-text behavior.
- [ ] Define unsaved, saving, saved, failed, offline, and conflict UX.
- [ ] Decide whether autosave exists and define its semantics separately from local draft persistence.
- [ ] Define browser-draft storage, expiry, cleanup, privacy, and multi-tab rules if used.
- [ ] Define rejected-conflict storage, retention, comparison, and cleanup.
- [ ] Define complete-content save request/response and safe error categories.
- [ ] Define renderer escaping, paragraph/line-break presentation, CSP, and cache behavior.
- [ ] Define counts, excerpts, search, comparison, and source-revision linkage.
- [ ] Define AI context text projection and manifest fields for format/revision identity.
- [ ] Specify plain-text, structured-archive, and derived export contracts.
- [ ] Define staged transformations and warnings for each supported import format.
- [ ] Define backup coverage and exact restoration validation for representation metadata.
- [ ] Create a representation-migration test fixture using synthetic content.
- [ ] Add unit, integration, end-to-end, security, accessibility, export, backup, and restoration tests described here.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes Django initialization, application code, models, migrations, forms, views, templates, JavaScript, CSS, APIs, database objects, package installation, editor or frontend selection, exact normalization form, exact limits, production-data access, deployment, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No Django project, model, migration, form, view, template, JavaScript, CSS, API, database object, editor package, frontend framework, sanitizer, Markdown processor, export library, or deployment configuration is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
