# Strange Novelty Version 1 Data Model

## Purpose

This document defines the conceptual data model for Version 1 of Strange Novelty. It identifies the authoritative records, relationships, content states, provenance rules, revision expectations, portability requirements, and future extension points needed for a private creative workspace. It does not select a database product, define a physical schema, prescribe SQL, or create application code.

The model serves one author and artist. It must preserve authorial authority, privacy, contextual canon, provenance, recoverability, and useful exit paths while remaining small enough to implement and understand.

## Data-Model Goals

The Version 1 data model should:

- represent worlds, series, books, chapters, scenes, characters, and locations as distinct domain concepts;
- preserve stable identity independently from names, titles, ordering, or hierarchy location;
- make workspace ownership explicit;
- support scene drafting and revision without silent overwrites;
- preserve meaningful distinctions among all required content states;
- distinguish creative state from origin;
- support canon that varies by creative context;
- preserve enough provenance to explain origins and authority changes;
- require explicit author approval for authority-changing transitions;
- support links and dependable backlinks without becoming an unrestricted graph;
- support search and navigation across Version 1 content;
- make derived indexes and backlinks rebuildable from authoritative records;
- support concurrent tabs or devices without last-write-wins data loss;
- support documented exports, complete backups, verification, tested restoration, and migration;
- retain enough history to recover from common editing mistakes;
- allow future capabilities through deliberate, typed extensions; and
- avoid assumptions specific to the old Story Engine or any particular story.

Shared metadata may be modeled consistently, but the model must not reduce World, Series, Book, Chapter, Scene, Character, Location, Link, Revision, Provenance, and other domain concepts to one generic entity table.

## Model Boundaries

Version 1 includes one private author-owned workspace; the narrative hierarchy; scene drafting and revision; Character and Location records; supported links and backlinks; contextual content states; basic authored, imported, and AI-generated provenance; import and AI-suggestion staging; searchable metadata and derived indexes; authority-related audit information; and the metadata needed for export, backup, restoration, and migration.

Version 1 does not model every possible story fact, relationship, asset, or continuity concern. Timelines, secrets and reveals, character knowledge, factions, items, creatures and species, artwork, maps, and research are future extensions.

## Core Identity Rules

### Workspace identity

Every authoritative creative record belongs to exactly one Workspace. The Workspace is the root ownership and privacy boundary for narrative records, entities, links, revisions, imports, AI suggestions, exports, and backups.

Version 1 supports one authorized human owner per Workspace. Ownership must not be inferred from a browser session, filesystem location, display name, or current parent. Records from different Workspaces must not be linked, reparented, searched together, exported together, or included together in AI context unless a later approved feature defines a secure cross-workspace operation.

### Record identity

Every authoritative record has a stable identifier that:

- is unique within a documented namespace;
- is assigned on creation or acceptance into authoritative storage;
- survives rename, reorder, move, archival, deprecation, export, restoration, and migration;
- is not derived from editable names, titles, sequence numbers, or paths;
- is never reused after deletion;
- is preserved by backup and restoration; and
- can be mapped explicitly to identifiers from imports.

Names, titles, slugs, paths, and sequence numbers are attributes, not identity.

### Identity after copying

A deliberate duplicate is a new record with a new identifier. Provenance may refer to the source record. Restoration of the same Workspace preserves identifiers. Import into a different Workspace must explicitly choose between identity-preserving restoration and creation of new identities.

### Type identity

An identifier refers to a typed domain record, not an untyped node. Domain types cannot be silently changed to avoid a deliberate migration.

## Stable Identifiers

Stable identifiers are used for hierarchy relationships, links, revisions, provenance, contextual states, imports, AI records, manifests, restoration checks, concurrency checks, and migrations.

Links must reference identifiers, never names alone. Exports may include human-readable name snapshots, but those snapshots are not authoritative link targets. Identifiers must remain opaque to creative meaning and must not encode editable hierarchy or state. The exact identifier format remains undecided.

## Workspace Ownership

The Workspace owns Worlds, Series, Books, Chapters, Scenes and revisions, Characters, Locations, Links, contextual-state assignments, provenance, import batches, staged imports, AI operations and suggestions, required audit events, and export and backup metadata.

All state-changing operations must verify Workspace ownership at the application-server boundary. Workspace deletion, archival, export, backup, and restoration are high-impact operations and must not be implemented as unprotected cascades.

## Common Record Metadata

Where applicable, records should include a stable identifier, Workspace identifier, domain type, display name or title, creation and modification timestamps, concurrency version, archive or deletion status, current content-state information, provenance, and a current revision reference.

Not every type needs every field. Common metadata is a consistency vocabulary, not a replacement for typed records.

## Narrative Hierarchy

The hierarchy consists of World, Series, Book, Chapter, and Scene. It is the primary browsing structure, not unrestricted containment. It provides valid organizational paths without requiring authors to create artificial Series or World records. Parent-child references use stable identifiers and siblings have explicit author-controlled order. Reordering does not change identity. Cross-cutting relationships use supported Links rather than extra hierarchy parents.

### World

A World is the highest narrative scope. It may contain Series and be associated with Characters, Locations, and contextual states. It does not imply that every statement is universally canon.

A World supports identity, Workspace ownership, name, optional description, ordering metadata, applicable state, provenance, timestamps, and archive and recovery status. It does not encode story-specific cosmology, eras, or old Story Engine assumptions.

### Series

A Series optionally organizes Books within a World. It supports identity, Workspace ownership, a parent World identifier, name, optional description, explicit order, applicable state, provenance, timestamps, and archive and recovery status.

Version 1 uses one direct World parent for each Series. Cross-world relationships require a later approved model.

### Book

A Book organizes Chapters and has exactly one primary organizational parent in Version 1. Its parent is either a Series, a World, or the Workspace. Series membership is optional: a standalone Book may belong directly to a World, or directly to the Workspace when no World is appropriate. A Book supports identity, Workspace ownership, a typed primary-parent reference, title, optional description, explicit order within its parent context, applicable state, provenance, timestamps, and archive and recovery status.

Moving a Book between valid parent contexts changes only its primary-parent reference and ordering metadata. The move preserves the Book's stable identity, Links, provenance, Chapter and Scene structure, Scene revision history, and other history associated with the Book.

Edition behavior is deferred, but Book identity must permit later edition or snapshot records to refer to it.

### Chapter

A Chapter organizes Scenes within a Book. It supports identity, Workspace ownership, a parent Book identifier, title or label, optional summary or notes, explicit order, applicable state, provenance, timestamps, and archive and recovery status. Chapter numbers are attributes, not identifiers.

### Scene

A Scene is the primary drafting unit. It belongs to one Chapter and supports identity, Workspace ownership, a parent Chapter identifier, title or label, current content or current-revision reference, optional summary or notes, explicit order, content state, provenance, timestamps, concurrency version, and archive and recovery status.

A Scene may link to supported Scenes, Characters, and Locations. Moving it preserves identity and revision history. Version 1 does not assume that a Scene's draft state determines the truth status of every fact in its prose.

## Version 1 Structured Entities

Character and Location are explicit typed entities. They share identity, states, provenance, search, linking, archival, and timestamp behaviors but remain distinct types. Version 1 has no generic custom-entity builder.

### Character

A Character represents a person or person-like participant. It supports identity, Workspace ownership, primary name, optional aliases, short description, optional longer notes, explicit association with relevant Worlds, contextual state, provenance, timestamps, and archive, deprecation, and recovery status.

Names are not unique identity. Version 1 does not hard-code roles, species, relationship taxonomies, knowledge states, or story-specific biography templates.

### Location

A Location represents a place. It supports identity, Workspace ownership, primary name, optional aliases, short description, optional longer notes, explicit association with relevant Worlds, contextual state, provenance, timestamps, and archive, deprecation, and recovery status.

Names are not unique identity. Version 1 does not require a fixed geographic hierarchy, coordinate system, map provider, or story-specific taxonomy.

## Links and Backlinks

### Link model

A Link is an explicit directional relationship between supported records. Version 1 endpoints are Scene, Character, and Location.

A Link includes its own identifier, Workspace, source type and identifier, target type and identifier, a bounded system-defined relationship kind where needed, optional author note or label, provenance, timestamps, and archive or deletion status.

The initial relationship vocabulary must be small and understandable. Links are not inferred solely from names or matching text; automated possible links remain suggestions until accepted. The model prevents cross-Workspace links, missing endpoints, name-based identity, unexplained duplicates, and unsupported endpoint-kind combinations.

### Backlinks

A Backlink is the reverse view of an authoritative Link. Backlinks may be queried directly or maintained in a derived lookup or index. If materialized, they remain rebuildable derived data.

Link changes must update or invalidate derived backlinks within a documented consistency boundary. Any delay must be bounded, unable to change authority, detectable, and repairable. Exports or backups may include backlinks for convenience, but restoration must rebuild them from Links. On disagreement, authoritative Links prevail and verification reports the mismatch.

### No unrestricted graph

Version 1 does not support arbitrary endpoint types, user-defined relationship schemas, executable relationship semantics, graph-wide inference, automatic transitivity, or a general graph editor. New types and relationship meanings require explicit model changes.

## Content States

Content state describes creative authority or working status. It is distinct from provenance, origin, hierarchy, archival status, and revision history. Editing imported or AI-generated material does not erase or replace its original provenance.

Imported content and AI suggestions may transition to Draft, Idea, Speculation, Deprecated content, or Canon only through an explicit author action. Any promotion to Canon must record the author approval event, its timestamp, the prior state, the resulting Creative Context, and the retained origin provenance.

### Canon

Canon is content explicitly accepted by the author as authoritative within a defined Creative Context. It is never assumed to be global.

### Speculation

Speculation is a developed possibility under consideration but not accepted as true. Conflicts remain visible for author review.

### Idea

Idea is an undeveloped creative thought. Author-written origin does not make an Idea authoritative.

### Draft

Draft is author-controlled material being written or revised. Draft does not mean imported, AI-generated, or canonical.

### Imported content

Imported content came from outside the authoritative Workspace and has not had its authority established. Parsing, matching, editing, or hierarchy placement does not promote it.

### Deprecated content

Deprecated content is retained for history or reference but is no longer current in its applicable context. Deprecation is not deletion.

### AI suggestion

AI suggestion is model-generated content not accepted into another state. Every retained generated result begins in this state and cannot become Canon automatically.

## Contextual Canon

Content state, especially Canon, applies within an explicit Creative Context. Version 1 must support contexts anchored to Workspace, World, Series, and Book while leaving room for timeline, edition, alternate continuity, point of view, period, and other approved context types. A Book-level Creative Context applies equally to a standalone Book whose primary parent is a World or the Workspace and to a Book whose primary parent is a Series.

A contextual-state assignment includes the classified record or content identifier, state, context type, context-anchor identifier where applicable, author action or provenance event, timestamps, optional note, and active, superseded, or deprecated status.

Appearance in a Chapter or Scene does not establish broader Canon. A narrower assignment does not automatically apply more broadly. Any future inheritance must be explicit, understandable, and reversible. Conflicts are preserved and surfaced, never silently resolved.

## Provenance

Provenance explains origin, development, and authority. It is separate from current state. Editing or reclassifying imported or AI-generated material does not erase imported or AI-generated origin.

At minimum, provenance preserves origin category, creation time, creating actor or process, known source reference, applicable import or AI operation, derivation source, author review status, authority-changing actions, and significant transition history. Internal references use stable identifiers.

### Author-written origin

Author-written origin means the author created the material directly as new content. Later comparison or AI assistance does not erase that origin. Substantial derivatives should retain their source relationship where practical.

### Imported origin

Imported provenance records, where known, source type and description, safe source reference, batch, import time, external identifier, format version, transformations, warnings, unresolved mappings, and author disposition.

Old Story Engine material always enters with imported origin and Imported content state until explicitly reviewed. Presence in that system is not evidence of Canon.

### AI-generated origin

AI provenance must retain enough metadata to explain and audit the operation. Subject to security and retention policy, this may include the operation, task, invocation time, provider and model identifiers, bounded source identifiers, context manifest or selection rule, instruction version, result reference, author disposition, and derived records. Provider and model identifiers may be retained when permitted, but credentials, tokens, keys, and other secret values must never be stored in provenance.

Full prompts, full responses, and sensitive source text must not be retained indefinitely unless an approved security and retention policy explicitly requires and permits that retention. Provenance should prefer stable source references, bounded manifests, summaries, hashes, or other privacy-conscious metadata when those are sufficient to explain the operation.

AI-generated origin is durable. Editing or reclassification must not rewrite history to claim original authorship.

## State-Transition Rules

Every transition records the affected identifier, prior and new state and context, initiating author or process, required approval, timestamp, optional reason, and base concurrency version. Importers, AI providers, background jobs, indexers, and migrations may not silently promote authority.

### Authority-changing transitions

Explicit author approval is required to promote to Canon, broaden Canon context, supersede Canon, restore Deprecated content as current authority, accept imported or AI material into an author-controlled state, or overwrite authoritative material.

Approval cannot be inferred from viewing, saving an unrelated edit, successful import, invoking AI, linking to Canon, hierarchy placement, editing staged material, restoration, or migration.

### Imported-content transitions

Imported content may remain imported, be revised with imported origin retained, transition explicitly to another state, or be rejected, archived, or deleted. Bulk import cannot default it to Canon.

### AI-suggestion transitions

An AI suggestion may be retained, rejected, revised with origin retained, copied to a new author-controlled item with derivation provenance, explicitly transitioned, archived, or deleted. Accepting a suggestion is not synonymous with making it Canon.

### Deprecation transitions

Deprecation preserves former state, context, author action, time, optional replacement, provenance, and revisions. Restoring current authority requires explicit approval.

## Scene Drafting and Revision

Scene identity is separate from Scene Revision identity. A Scene retains narrative identity, placement, metadata, links, state, and its current-revision reference. A Scene Revision retains its identifier, Scene and Workspace, content, creation time, creator, base revision, ordering, save source where useful, provenance, and current status.

The exact content format and revision storage strategy remain undecided.

### Saving and conflict detection

Editable records expose a concurrency version or change token, and writes identify their base version. If another tab, device, job, or session has changed the record, the stale write must not silently overwrite it.

The application must report a conflict, preserve the attempted content where practical, enable comparison or deliberate resolution, and create a revision only after resolution. Automatic last-write-wins is prohibited. Real-time collaboration and automatic text merging are not required.

### Revision meaning

A saved revision records content history; it does not change state or establish Canon. Revision history follows the Scene through moves, renames, archival, deprecation, export, backup, and restoration.

## Revision History and Recovery Expectations

Version 1 supports retrieving prior Scene revisions, identifying the current revision, inspecting enough metadata to select a recovery point, and restoring prior content as a new current revision without erasing intervening history. It retains Scene identity, hierarchy, and restoration provenance and detects incomplete revision chains.

Retention, autosave frequency, snapshots, diffs, and compaction remain open. Revision history addresses editing mistakes; backup addresses broader loss. Both participate in restoration planning.

## Searchable Fields and Indexing Concepts

Version 1 search covers Scenes, Characters, and Locations. Searchable fields include Scene title, content, summary, and notes; Character name, aliases, description, and supported profile text; and Location name, aliases, description, and supported profile text.

Useful filters or result metadata include domain type, hierarchy context, content state, Creative Context, archival or deprecation status, origin, and timestamps. Results use stable identifiers and remain unambiguous when names duplicate.

Search indexes are rebuildable derived data and never the sole copy of creative content, Links, states, or provenance. Asynchronous updates require a documented consistency boundary and detectable repair. Semantic search, embeddings, graph ranking, and continuity inference are outside Version 1.

## Deletion, Archival, Deprecation, and Recovery

### Archival

Archival removes an item from normal active views without invalidating its creative assertions. Archived records preserve identity, state, provenance, Links, revisions, recovery, and documented export and backup behavior.

### Deprecation

Deprecation is a creative-state decision. Deprecated records remain navigable through appropriate links, filters, history, provenance, exports, and backups.

### Soft deletion

Ordinary deletion first creates a recoverable trash state. Soft-deleted records retain identifiers during the recovery period, leave normal views, cannot be active Link targets, and preserve relationships needed for recovery.

Deleting a record with children or active Links must not silently orphan or cascade-delete creative records. The operation must be blocked or present an explicit reviewable plan.

### Permanent purge

Purge is a separate destructive operation with explicit confirmation. It must address children, Links, revisions, provenance, staged-operation references, and backup retention. Identifiers are never reused. Existing retained backups may still contain purged material, which must be communicated honestly.

### Recovery

Recovery restores the original identifier for the same logical record where safe and reconciles hierarchy, order, content, revisions, state, context, provenance, Links, backlinks, and indexes.

## Audit and Timestamps

Version 1 needs trustworthy history, not a complete forensic event-sourcing system. Applicable timestamps include creation, modification, archival, deletion, restoration, deprecation, author review, state transition, import, AI operation, export, backup, verification, and restoration.

Authority-changing audit events identify event type, record, Workspace, authenticated author or authorized process, prior and resulting state, timestamp, operation or provenance reference, concurrency version, and optional reason.

Operational logs are not authoritative audit history and must exclude unnecessary creative content. Exact time precision, retention, and storage remain undecided.

## Import Staging

Import is staged rather than written directly into authority. An Import Batch records identity, Workspace, source and format, times, initiating author, importer version, manifest, result counts, verification, warnings, errors, and disposition.

Staged items retain source identity, proposed type, source reference, parsed content, proposed parents and Links, unresolved mappings, transformation warnings, imported origin, Imported content state, and review status.

Import must not overwrite by name, canonize old Story Engine content, create cross-Workspace Links, hide discarded data, promote to Canon, or conceal partial failure. Committing reviewed items preserves batch provenance. The exact Version 1 import workflow remains open.

## AI Suggestion Staging

AI operations and results remain separate from source content. An AI Request identifies its operation, Workspace, task, explicit invocation, bounded sources, context rule or manifest, time, status, and approved provider metadata.

An AI Suggestion identifies its record, Workspace, operation, protected result, AI-generated origin, AI suggestion state, creation time, review status, disposition, proposed target, and derived records.

Creation never overwrites source material. Application passes through ordinary validation, conflict detection, provenance, transitions, and approval. Rejected-suggestion retention must be explicit.

## Export and Backup Representation Requirements

### Export representation

A documented export must preserve its format version, Workspace identity or export equivalent, stable identifiers, domain types, hierarchy and order, Scene content and documented revision scope, Characters, Locations, identifier-based Links, states, contexts, provenance, included lifecycle status, referenced objects, time, scope, and manifest.

Names may accompany but never replace references. Documented exports may omit irrelevant operational records but never include credentials, sessions, secrets, or unrelated logs. The final format remains undecided.

### Backup representation

A backup contains enough state to restore the Workspace: hierarchy; Scene content and required history; Characters and Locations; Links; contextual states; required provenance and audit events; required import and AI records; private objects; representation version; migration information; manifest; and integrity data.

Derived backlinks and indexes may be omitted if rebuildable. If present, they are marked derived and verified or rebuilt.

### Verification and restoration

Verification checks manifest readability, supported version, expected record groups, reference integrity, parent validity, Link endpoints, revision references, required objects, integrity data, and incomplete-operation markers.

A representative restoration test confirms usable hierarchy, order, Scene content and history, Characters, Locations, states and contexts, Links and backlinks, provenance, and lifecycle behavior. Backup is incomplete until restoration has passed.

## Versioning and Migration Requirements

Application data, exports, and backups are explicitly versioned with format name, version, useful application version, migration needs, compatibility constraints, and integrity metadata.

Migrations must be deterministic where practical; preserve identifiers, origin, authority, hierarchy, Links, states, contexts, and revisions; report transformations and failures; avoid silent promotion or field loss; be safely retryable or recoverable; and be tested with representative data and a verified recovery point.

A migration may change representation but not silently change creative meaning. Unsupported versions fail clearly rather than being partially interpreted.

## Future Support

Future capabilities extend the typed model through explicit records and bounded relationships, not generic nodes or arbitrary graph semantics.

### Timelines

Future Event, Timeline, and temporal-placement records must keep story chronology separate from reader reveal and character knowledge. Timeline context may extend Creative Context without changing existing identities.

### Secrets and reveals

Future Secret and Reveal records distinguish underlying information, truth status, reader reveal position, and the narrative record performing the reveal. Reveal is not inferred from story chronology.

### Character knowledge

Future Character Knowledge records represent what a Character knows, believes, suspects, misunderstands, or forgets in a context. Knowledge is not inferred solely from Canon or reader revelation.

### Factions

Faction may become a distinct type. Membership, allegiance, and conflict use bounded typed relationships.

### Items

Item may become a distinct type. Ownership, possession, location, and significance may need time-aware relationships.

### Creatures and species

Creature and Species require deliberate types that can distinguish an individual from a category rather than forcing both into Character.

### Artwork

Artwork uses typed metadata linked to private objects and preserves identity, ownership, provenance, rights, state, export, backup, and restoration.

### Maps

Map is a typed private asset. Pins and spatial references use Location identifiers, not names.

### Research

Research is a distinct source-oriented concept with citation, origin, rights, and privacy metadata. It remains distinguishable from story Canon.

## Explicit Non-Decisions

This document does not decide:

- the database product, physical storage paradigm, schema, or SQL;
- stable-identifier format or physical shared-metadata representation;
- Scene content or editor format;
- revision storage, retention, autosave, snapshots, diffs, or compaction;
- the exact concurrency mechanism or automatic merge behavior;
- final relationship kinds, uniqueness rules, or backlink implementation;
- search technology, ranking, tokenization, or index timing;
- export or backup format, storage, encryption, schedule, or retention;
- supported import formats or whether Version 1 exposes general import;
- the first AI task or AI-record retention;
- authentication, authorization, or object-storage implementation;
- trash, purge, or audit retention periods;
- edition, timeline, or custom-context semantics;
- advanced fact, assertion, contradiction, or continuity models; or
- any technology-stack choice.

These require later architecture work or decision records before implementation depends on them.

## Open Questions

1. Must every Series belong to exactly one World in Version 1, or should Workspace-level Series also be allowed?
2. When a Book moves between Series, World, and Workspace parent contexts, what validation and ordering rules must apply?
3. Should Characters and Locations associate with one World, multiple Worlds, or a primary World plus additional associations?
4. Which states apply to entire records, and does Version 1 need field- or assertion-level states?
5. Which Creative Context levels must the Version 1 interface expose?
6. Should broader contexts provide defaults, and how should contextual conflicts appear?
7. Which Link kinds and endpoint combinations are required?
8. Can identical endpoint-and-kind Links occur more than once?
9. How are backlinks derived, and what consistency delay is acceptable?
10. Which Scene content and revision strategy best supports drafting, export, migration, and recovery?
11. How long are revisions and soft-deleted records retained?
12. What conflict-resolution experience is required across tabs or devices?
13. Which fields are required for Character and Location, and are aliases first-class revisioned values?
14. What bounded import workflow, if any, belongs in Version 1, and how are possible matches reviewed?
15. Which AI inputs, outputs, and provider details are retained for provenance and privacy?
16. Does applying an AI suggestion create a record, a revision, or either through an explicit choice?
17. Which export format best balances readability, stable linking, structure, and re-import?
18. Which revisions, deleted records, import records, and AI records belong in author-facing exports?
19. What constitutes a complete backup, and which derived data should be rebuilt?
20. What representative dataset and checks define successful restoration?
21. What format compatibility window and migration policy are required?
22. Which audit events and retention periods are necessary?
23. Which durable decisions require architecture decision records before implementation?
