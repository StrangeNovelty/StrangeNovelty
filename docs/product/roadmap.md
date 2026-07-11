# Strange Novelty Product Roadmap

## Purpose

This roadmap describes a conservative, dependency-aware path from the current documentation foundation to the long-term Strange Novelty product vision.

The phases are ordered to establish privacy, authorial control, data ownership, provenance, and recovery before adding broader automation or integrations. A later phase may be refined as the product develops, but it should not bypass unfinished foundations from an earlier phase.

This roadmap communicates sequence and intent. It is not a promise that every deferred capability will be built.

## Roadmap Rules

The following rules apply across all phases:

- The author remains the final authority over creative decisions.
- AI output never becomes canon automatically.
- Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion remain meaningfully distinct.
- Private creative material must receive conservative security and privacy protections.
- AI context must be narrow, deliberate, understandable, and appropriate to the requested task.
- Integrations must not become the sole custodians of the author’s work.
- Export, backup, restoration, and migration paths are product capabilities, not afterthoughts.
- Each phase should deliver the smallest coherent workflow that satisfies its exit criteria.
- Work from a later phase should not begin merely because an earlier phase is difficult or incomplete.
- A phase may be split into smaller milestones when that reduces risk without weakening its exit criteria.
- Changes to durable scope, product behavior, architecture, data, security, AI context, or integration boundaries require corresponding documentation updates.
- If a scope change affects an established decision, the relevant architecture decision record must also be added or updated before implementation proceeds.

## Phase Dependencies

The roadmap follows this general dependency chain:

1. Phase 0 establishes the documented product and technical foundations.
2. Phase 1 implements the first complete, private, recoverable writing workflow.
3. Phase 2 builds richer knowledge and continuity features on the stable Phase 1 hierarchy, entities, links, states, and provenance.
4. Phase 3 expands AI assistance only after the product can assemble and classify trustworthy context.
5. Phase 4 adds visual material using the established security, provenance, linking, export, and backup models.
6. Phase 5 adds generators only after structured entities and bounded AI workflows are dependable.
7. Phase 6 adds external services only after Strange Novelty is independently usable and durable.
8. Phase 7 adds publishing and production workflows after the content model, exports, snapshots, and external boundaries are mature.

Later-phase discovery may inform earlier architecture decisions. It must not silently move later-phase implementation into the current scope.

## Phase 0 — Product and Architecture Foundations

### Objective

Establish the documented decisions and boundaries required to create application code responsibly.

### Planned Work

- Complete the core product documentation.
- Define the application architecture.
- Define the data model.
- Define the security model.
- Define AI context and retrieval rules.
- Define external integration boundaries.
- Establish the architecture decision record process.
- Record significant product and architecture decisions.
- Choose the technology stack only after the relevant product, architecture, data, security, AI, and operational decisions are documented.

### Entry Criteria

- The product vision and principles exist.
- The repository is documentation-only.
- No application implementation constrains the architecture prematurely.

### Exit Criteria

- Version 1 scope and acceptance criteria are documented and approved.
- The roadmap is documented and approved.
- The architecture overview defines the major components, trust boundaries, and deployment shape.
- The initial data model defines the core hierarchy, scenes, characters, locations, links, content states, and provenance.
- The security documentation defines authentication, authorization, session handling, secret handling, storage protection, logging boundaries, backup protection, and relevant threat assumptions.
- AI context rules define task-specific selection, context preview expectations, provenance, output classification, and prohibited behavior.
- Integration boundaries explain how future external services may connect without becoming the sole source of truth.
- The decision-record process is documented.
- Major technology choices and their tradeoffs are recorded as architecture decisions.
- Export, backup, verification, and restoration approaches are defined well enough to implement and test.
- The initial application milestone can be built without relying on undocumented durable decisions.

### Dependencies

Phase 0 depends on the existing product vision and principles. Every later phase depends on its exit criteria.

## Phase 1 — Private Writing Workspace

### Objective

Deliver the first complete, private, secure, and recoverable creative workflow for one author and artist.

### Planned Work

- Secure single-user authentication.
- Worlds, series, books, chapters, and scenes.
- Scene drafting and revision.
- Characters and locations as the first structured story entities.
- Links and backlinks among supported scenes, characters, and locations.
- Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion states.
- Basic provenance for authored, imported, and AI-generated material.
- Search and navigation across the supported hierarchy and entities.
- Export in a useful, documented format.
- Backup creation and verification.
- Documented and tested restoration.
- One narrow, explicitly invoked AI capability.

### Entry Criteria

- Phase 0 exit criteria are satisfied.
- Version 1 architecture, data, security, and AI context decisions are documented.
- The technology stack has been selected through recorded decisions.
- The first implementation milestone has bounded acceptance criteria.

### Exit Criteria

- A single authorized user can securely sign in and sign out.
- Unauthenticated access to private creative material is denied.
- The author can create, view, update, organize, and navigate the core hierarchy.
- The author can draft and revise scenes.
- The author can create, update, search, and navigate characters and locations.
- Supported links expose usable backlinks.
- All required content states are visible and intentional.
- Imported content and AI suggestions cannot become canon without explicit author action.
- Basic provenance distinguishes authored, imported, and AI-generated material.
- Search and navigation support the core Version 1 journeys.
- The narrow AI capability uses visible, task-specific context and produces reviewable AI suggestions without autonomous rewriting.
- Export has been verified against representative content.
- Backup creation and verification are operational.
- Restoration has been tested using representative data.
- Restored data retains essential hierarchy, content, states, links, and provenance.
- The documented Version 1 acceptance criteria are satisfied on supported desktop and laptop browsers.
- Known security and data-loss risks have been reviewed and either resolved or explicitly accepted and documented.

### Dependencies

Phase 1 depends on all Phase 0 foundations. Phase 1 is the minimum usable product and must be complete before broader knowledge, AI, visual, integration, or publishing work is treated as active scope.

## Phase 2 — Knowledge and Continuity Foundation

### Objective

Extend the stable writing workspace with richer structured knowledge and review-oriented continuity support.

### Planned Work

- Additional structured entity types selected from demonstrated author needs.
- A basic story timeline.
- Secrets and reveals as explicit, distinguishable concepts.
- Stronger search across structured and narrative material.
- Import review workflows.
- Continuity support that surfaces possible issues for author review.
- Richer provenance and change history.

### Entry Criteria

- Phase 1 exit criteria are satisfied.
- The author has used the Phase 1 workflow enough to identify recurring knowledge-management needs.
- Proposed entity and continuity additions have bounded user journeys.
- Data-model changes and migration requirements are documented.
- Existing export, backup, and restoration processes can accommodate the proposed changes.

### Exit Criteria

- Approved additional entity types are usable without requiring an unrestricted custom entity system.
- The author can record and navigate a basic timeline without conflating event order, reveal order, and character knowledge.
- Secrets and reveals remain explicit and reviewable.
- Search improvements produce useful results across the expanded content model.
- Imported material remains marked as imported until the author reviews it.
- Continuity tools present observations or questions rather than automatic corrections.
- Richer provenance explains important origins, state transitions, imports, and revisions.
- Export, backup, and restoration preserve the expanded data model.
- Relevant product, architecture, data, security, and decision documentation is current.

### Dependencies

Phase 2 depends on the Phase 1 hierarchy, entity, link, state, provenance, search, and recovery foundations. It provides important context and provenance capabilities for the broader AI work in Phase 3.

## Phase 3 — Bounded AI Assistance

### Objective

Expand AI assistance while keeping context, cost, provenance, and creative authority explicit.

### Planned Work

- Task-specific context assembly.
- Spoiler-aware context selection.
- A visible context preview before submission where appropriate.
- AI suggestions with explicit accept and reject workflows.
- Usage and cost visibility.
- Provenance for AI inputs, outputs, and author actions.
- Continued prohibition of autonomous canon changes.

### Entry Criteria

- Phase 1 exit criteria are satisfied.
- The relevant Phase 2 knowledge, search, state, and provenance foundations needed by each AI task are complete.
- Each proposed AI capability has a bounded task, user journey, context-selection rule, privacy review, and acceptance criteria.
- External model-service boundaries, retention behavior, failure behavior, and cost controls are documented.
- The author can identify what material will be sent and why.

### Exit Criteria

- Every supported AI task uses a defined, task-specific context assembly process.
- Spoiler boundaries are respected where the task depends on reader reveal or character knowledge.
- The author can inspect or clearly understand the context used for supported AI requests.
- AI output is classified as an AI suggestion and retains useful provenance.
- Accept, reject, revise, and retain-as-suggestion workflows are explicit.
- Accepting a suggestion does not silently make it canon.
- Usage and cost information is understandable enough to support informed use.
- Failures do not silently alter source content.
- No supported AI feature autonomously rewrites authoritative material or changes canon.
- Security, export, backup, and restoration behavior has been verified for AI-related records.

### Dependencies

Phase 3 depends on the Phase 1 content-state, provenance, security, and recovery foundations. Individual Phase 3 capabilities may also depend on specific Phase 2 timeline, reveal, knowledge, search, import, or provenance work.

## Phase 4 — Visual Worldbuilding

### Objective

Add private visual-reference and spatial-worldbuilding capabilities without weakening ownership, provenance, or portability.

### Planned Work

- An artwork library.
- Map uploads.
- Links between locations and maps.
- Map pins for supported locations.
- Media provenance.
- Rights and usage metadata.
- Visual asset export.

### Entry Criteria

- Phase 1 security, entity linking, export, backup, and restoration are stable.
- Storage and delivery rules for private media are documented.
- Supported file types, size limits, metadata, and threat controls are defined.
- Rights and provenance requirements are documented.
- The visual workflow has demonstrated value for the author.

### Exit Criteria

- The author can securely upload, view, organize, and remove supported artwork and maps.
- Locations can be linked to maps and represented by usable map pins.
- Media records preserve source, provenance, and rights metadata where applicable.
- Private media is not exposed publicly by default.
- Visual assets and relevant metadata can be exported in useful formats.
- Backup and tested restoration include visual assets and their relationships.
- Storage limits, failure behavior, and unsupported media are communicated clearly.

### Dependencies

Phase 4 depends on the Phase 1 security, links, provenance, export, backup, and restoration models. It may use entity improvements from Phase 2 but does not require generators from Phase 5.

## Phase 5 — Generators

### Objective

Provide bounded structured creative assistants whose output remains reviewable and subordinate to the author.

### Planned Work

- An NPC generator.
- A city generator.
- A creature generator.
- Other structured creative assistants justified by real use.
- Review workflows for generated material.
- Provenance and state handling for generated outputs.

### Entry Criteria

- Phase 3 bounded AI workflows are stable.
- Relevant Phase 2 structured entity types exist or are explicitly approved.
- Each generator has a defined creative purpose, input boundary, output schema, cost boundary, and review workflow.
- Generated material can be exported, backed up, restored, and deleted predictably.

### Exit Criteria

- Each generator operates only when explicitly invoked.
- Inputs and relevant context are visible or clearly described.
- Every generated result begins as an AI suggestion.
- Generated material does not overwrite existing content or become canon automatically.
- The author can accept, reject, revise, retain, or delete generated material.
- Accepted material retains useful provenance.
- Usage and cost are visible where external services are involved.
- Export, backup, and restoration preserve generated records and their provenance.

### Dependencies

Phase 5 depends on Phase 3 task-specific AI context, suggestion review, cost visibility, and provenance. Individual generators also depend on the relevant structured entity types from Phase 2.

## Phase 6 — External Integrations

### Objective

Connect Strange Novelty to selected external services without surrendering privacy, clarity, ownership, or source-of-truth control.

### Planned Work

- Google Drive integration.
- Google Docs integration.
- Email workflows.
- Narrow permissions and least-privilege authorization.
- Clear synchronization behavior.
- Explicit conflict detection and handling.
- Provenance for externally sourced or synchronized content.
- Revocation, disconnection, and recovery behavior.

### Entry Criteria

- Strange Novelty is independently usable without external integrations.
- Core export, backup, and restoration are stable.
- Each integration addresses a demonstrated workflow.
- Data-flow, permission, retention, sync, conflict, and failure behavior are documented.
- Security and privacy reviews are complete.
- The author can disconnect an integration without losing the primary archive.

### Exit Criteria

- Each integration requests only the permissions needed for its documented workflow.
- The author can understand which external data is accessed, imported, exported, or synchronized.
- Sync direction and source-of-truth rules are explicit.
- Conflicts are surfaced for review and are not silently resolved.
- Imported external content remains distinguishable until reviewed.
- Credentials and tokens are stored and revoked safely.
- Disconnecting an integration leaves Strange Novelty usable.
- No external integration is the sole source of truth for the author’s work.
- Export, backup, and restoration remain functional without the external service.
- Integration failures do not silently delete, overwrite, publish, or reclassify creative material.

### Dependencies

Phase 6 depends on Phase 1 ownership, security, import-state, export, backup, and restoration foundations. It benefits from Phase 2 import review and richer provenance. Integration-specific AI behavior must also follow Phase 3 context rules.

## Phase 7 — Publishing and Production

### Objective

Support deliberate movement from the private creative workspace into manuscript, submission, edition, and publishing workflows.

### Planned Work

- Manuscript compilation.
- DOCX export.
- EPUB export.
- Print-oriented export and layout support.
- Edition snapshots.
- Submission workflows.
- Publishing workflows.
- Production-oriented validation and metadata.

### Entry Criteria

- The writing and organization model is stable.
- Export architecture supports deterministic, testable transformations.
- Edition and snapshot semantics are documented.
- Publishing workflows have demonstrated author value.
- Format-specific requirements, validation, and maintenance costs are understood.
- Private working material remains separable from deliberate publication outputs.

### Exit Criteria

- The author can compile selected manuscript content in an intentional order.
- DOCX, EPUB, and approved print-oriented outputs satisfy documented validation criteria.
- Edition snapshots preserve the content and metadata needed to reproduce an edition.
- Submission and publishing actions require explicit author initiation.
- Publication outputs remain distinguishable from private drafts and current working material.
- Failures do not silently alter the source manuscript.
- Exported editions have documented provenance.
- Backup and restoration preserve edition and production records.
- Publishing workflows do not make a vendor the sole custodian of the work.

### Dependencies

Phase 7 depends on the stable Phase 1 hierarchy, drafting, export, backup, and restoration capabilities. Edition snapshots may depend on richer Phase 2 provenance. Google-based submission workflows may depend on selected Phase 6 integrations.

## Explicitly Deferred Items

The following items are not in the active Phase 0 scope and must not be implemented without an approved scope change:

- all Phase 1 application code;
- advanced timeline analysis;
- advanced reader-reveal analysis;
- advanced character-knowledge analysis;
- unrestricted or user-defined entity builders;
- graph editors;
- advanced semantic search;
- artwork generation;
- advanced digital asset management;
- generated maps;
- real-time collaboration;
- team and organization features;
- public sharing;
- native mobile applications;
- migration of all Story Engine data;
- automatic treatment of old Story Engine content as current canon;
- autonomous rewriting;
- autonomous continuity correction;
- automatic canon promotion;
- plugin systems;
- third-party integrations not explicitly approved and documented;
- publishing automation beyond the bounded Phase 7 workflows.

Placement in a future phase does not authorize implementation. Each item remains deferred until its entry criteria are satisfied and the scope change is explicitly approved.

## Scope Change Rule

Any change to the active phase or its committed scope requires documentation updates before implementation begins.

At minimum:

- update this roadmap when phase timing, order, dependencies, or deliverables change;
- update `docs/product/scope.md` when Version 1 boundaries or acceptance criteria change;
- update the relevant architecture documents when technical boundaries change;
- add or update architecture decision records when a durable decision or tradeoff changes;
- document effects on privacy, security, provenance, AI context, export, backup, and restoration;
- identify newly deferred work and any displaced commitments.

A verbal idea, exploratory note, prototype, or future-phase roadmap item does not move a feature into active scope.

## Current Phase

Strange Novelty is currently in **Phase 0 — Product and Architecture Foundations**.

The repository is documentation-only. Application code should not be created until the Phase 0 decisions needed for the first implementation milestone are documented and approved.

Current work should focus on completing the product, architecture, data, security, AI context, integration-boundary, decision-record, export, backup, and restoration foundations.

## Next Decisions

The following decisions are the most important ones to make before application code is created:

1. **Deployment and trust boundary**  
   Decide where the private web application will run, who operates it, how it is reached, and which systems are trusted with creative material.

2. **Application architecture**  
   Define the major application components, their responsibilities, and the boundary between browser, server, storage, background work, AI services, and future integrations.

3. **Canonical data storage**  
   Choose the primary storage approach and document how structured data, scene content, revisions, links, provenance, and future media will be represented.

4. **Core data model**  
   Define identifiers, ownership, hierarchy, entity relationships, content states, contextual canon, provenance, and deletion or deprecation behavior.

5. **Draft and revision model**  
   Decide how scene edits, history, recovery, concurrency assumptions, and revision retention will work for a single-user system.

6. **Authentication and session model**  
   Select the single-user authentication approach and document credential storage, session expiration, account recovery, and protection against unauthorized access.

7. **Authorization model**  
   Define how the application consistently denies unauthenticated access and how future integrations or background processes receive narrowly scoped authority.

8. **Secret and configuration handling**  
   Decide where application secrets, database credentials, encryption material, and external-service tokens will live and how they will be rotated and excluded from source control.

9. **Privacy and logging boundaries**  
   Define what may be logged, what must never be logged, how long operational data is retained, and how sensitive creative content is protected.

10. **AI capability for Version 1**  
    Choose the one narrow AI task based on demonstrated usefulness, privacy risk, context clarity, implementation effort, and measurable acceptance criteria.

11. **AI context assembly and preview**  
    Define how sources are selected, limited, displayed or described, transmitted, classified, retained, and associated with AI outputs.

12. **External AI service boundary**  
    Decide which model service, if any, may receive private content and document retention, training-use, credential, cost, availability, and failure assumptions.

13. **Search approach**  
    Define the initial searchable fields and indexing strategy without prematurely committing to advanced semantic search.

14. **Export format**  
    Choose the initial documented export format and define how hierarchy, content, states, links, and provenance will be represented outside the application.

15. **Backup, verification, and restoration**  
    Define what constitutes a complete backup, how integrity is checked, how restoration is performed, and how restoration will be tested before Version 1 is accepted.

16. **Import boundary**  
    Decide whether Version 1 supports any bounded import workflow and ensure imported material cannot be mistaken for current canon.

17. **Technology stack**  
    Choose the application framework, language, database, authentication mechanism, testing approach, and deployment tooling only after the preceding constraints are sufficiently documented.

18. **Initial implementation milestone**  
    Define the smallest vertical slice that can prove secure access, durable storage, basic navigation, and recovery without expanding beyond Version 1 scope.

Each durable decision should be reflected in the relevant documentation and, where appropriate, an architecture decision record.
