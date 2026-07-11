# Strange Novelty Version 1 Scope

## Purpose

This document defines the scope of the first release of Strange Novelty.

Version 1 should establish a small, coherent, trustworthy creative workspace that one author and artist can use regularly. It should prove the product’s core model without attempting to deliver every capability described in the long-term product vision.

The first release prioritizes authorial control, privacy, clear content states, useful connections, secure access, and durable ownership of creative work.

## Primary User

The primary user is one author and artist.

Version 1 is designed for a solo creative workflow. It does not need organizational administration, team permissions, collaborative editing, approval chains, or enterprise features.

The product should optimize for focus, continuity, clarity, low maintenance, and trust.

## Application Boundary

Version 1 is a private web application accessible from desktop and laptop computers.

It should provide a usable experience in supported desktop-class web browsers. Native mobile applications and a mobile-first interface are not required.

The application is private by default and must require secure authentication. It must not expose creative material publicly or provide public sharing links.

## Core Hierarchy

Version 1 supports the following narrative hierarchy:

1. Worlds
2. Series
3. Books
4. Chapters
5. Scenes

The hierarchy provides the primary structure for browsing and organizing narrative work.

A world may contain multiple series, a series may contain multiple books, a book may contain multiple chapters, and a chapter may contain multiple scenes. The system should preserve clear parent-child relationships while allowing story entities to be linked across the hierarchy.

Version 1 does not need to support arbitrary hierarchy levels or user-defined structural types.

## Drafting and Revision

Version 1 supports drafting and revising scene content.

The author should be able to:

- create, view, edit, and retain scenes;
- organize scenes within books and chapters;
- revise scene content without losing its narrative context;
- distinguish draft material from accepted story facts;
- understand when content was created or last changed;
- recover from common editing mistakes through an appropriate history, versioning, or restoration mechanism.

Version 1 is not intended to replace every feature of a general-purpose word processor. Its writing experience should be dependable and sufficient for the core story workflow.

## Structured Story Entities

Characters and locations are the first structured story entities in Version 1.

The author should be able to create, view, edit, search, and navigate character and location records. Each record should support a useful core description and enough identifying information to distinguish it from similar records.

Additional structured entity types are deferred. Version 1 should not include a custom entity builder.

## Links and Backlinks

Version 1 supports explicit links among:

- scenes;
- characters;
- locations.

The author should be able to connect a scene to relevant characters and locations and create other supported connections where the data model permits them.

When one supported item links to another, the destination should expose a backlink. The author should be able to follow links in both directions and use them to understand where a character or location appears or is referenced.

Version 1 should keep relationships understandable. It does not need an unrestricted graph editor or a complex user-defined relationship schema.

## Content States

Version 1 preserves the following content states:

- **Canon** — accepted as currently true within the relevant creative context.
- **Speculation** — a possibility being considered but not accepted as true.
- **Idea** — an undeveloped creative thought.
- **Draft** — authored material being written or revised.
- **Imported content** — material brought in from another source whose authority has not been established.
- **Deprecated content** — retained for history or reference but no longer current.
- **AI suggestion** — machine-generated material not accepted by the author.

These states must remain visible and distinguishable.

Changing an item’s state must be an intentional action. In particular, imported content and AI suggestions must not become canon automatically.

Version 1 should support the relevant creative context for a state and avoid assuming that all canon is universally true across every world, series, book, timeline, or version.

## Basic Provenance

Version 1 records enough provenance to help the author understand the origin and history of important material.

Where applicable, the system should preserve:

- whether content was authored, imported, or generated as an AI suggestion;
- the source of imported content when known;
- creation and modification timestamps;
- the current content state;
- whether an authority-changing action was explicitly approved by the author.

Version 1 does not require a complete forensic audit system, but it must not erase the distinction between authored, imported, and AI-generated material.

## Search and Navigation

Version 1 provides search and navigation across its supported content.

The author should be able to:

- browse the world, series, book, chapter, and scene hierarchy;
- navigate between linked scenes, characters, and locations;
- see backlinks for supported links;
- search for scenes, characters, and locations using useful identifying text;
- open a relevant result without manually reconstructing its location in the hierarchy;
- understand the current item’s place within the workspace.

Advanced semantic search, graph visualization, and automated continuity analysis are not required for Version 1.

## Export, Backup, and Restoration

The author must be able to leave the product with their work.

Version 1 must provide:

- export in a useful, documented format;
- a documented backup process;
- a way to verify that a backup was created successfully;
- a documented restoration process;
- a restoration test using a representative backup;
- confirmation that restored content remains usable and retains essential structure, states, links, and provenance.

A backup capability is not complete until restoration has been tested successfully.

Version 1 must avoid making the creative archive dependent on an undocumented or inaccessible format.

## Authentication and Privacy

Version 1 requires secure authentication appropriate for a private, single-user web application.

The application must:

- deny unauthenticated access to private creative material;
- use conservative session and credential handling;
- avoid exposing secrets in source control, logs, exports, or client-visible configuration;
- protect private content in storage and transit using appropriate security controls;
- avoid public sharing behavior;
- minimize collection and retention of unnecessary sensitive data.

Private story files belong under `private-data/` and must never be committed to the repository.

## AI Assistance

Version 1 includes one narrow, deliberate AI-assistance capability that supports the core creative workflow.

The capability must:

- operate only when explicitly invoked by the author;
- use a limited, understandable set of context;
- show or clearly describe which sources are included;
- avoid ingesting an entire story directory indiscriminately;
- classify its output as an AI suggestion;
- preserve relevant provenance;
- require author review before its output changes authoritative material;
- fail without silently changing source content.

The exact first AI task should be selected during product and architecture planning based on demonstrated usefulness, privacy, implementation risk, and the ability to define a narrow context boundary.

Version 1 must not provide autonomous rewriting. AI must not silently modify manuscripts, overwrite source material, resolve conflicts automatically, or promote its own output to canon.

## Version 1 User Journeys

### 1. Start and Organize a Project

The author signs in, creates a world, and organizes a series, book, chapters, and scenes within it. The author can return later and navigate the same structure without losing context.

### 2. Draft and Revise a Scene

The author opens a scene, drafts or revises its content, saves the work, and can confirm that the latest revision is retained. The author can identify the scene’s place within its world, series, book, and chapter.

### 3. Create Story Entities

The author creates character and location records, adds useful descriptive information, and finds those records again through browsing or search.

### 4. Connect Story Material

The author links a scene to characters and locations involved in it. From a character or location, the author can see and follow backlinks to the related scenes.

### 5. Classify Content

The author assigns or changes a supported content state. Imported content and AI suggestions remain visibly distinct from canon until the author explicitly changes their status.

### 6. Find Existing Material

The author searches for a scene, character, or location and opens the relevant result. The author can also navigate through hierarchy links and backlinks.

### 7. Request AI Assistance

The author explicitly invokes the supported AI capability, reviews the proposed context, receives an output marked as an AI suggestion, and decides whether to retain, reject, revise, or reclassify it.

### 8. Export Creative Work

The author exports supported content in a documented, useful format and can inspect the exported result without relying on the running application.

### 9. Back Up and Restore the Workspace

The author creates and verifies a backup. Using the documented restoration process, the workspace can be restored to a working state with its essential hierarchy, content, states, links, and provenance intact.

## Acceptance Criteria

Version 1 is acceptable when all of the following are true:

- A single authorized user can securely sign in and sign out.
- Unauthenticated users cannot access private creative content.
- The author can create, view, update, organize, and navigate worlds, series, books, chapters, and scenes.
- The author can draft and revise scene content.
- The author can create, view, update, search, and navigate characters and locations.
- The author can link supported scenes, characters, and locations.
- Supported linked items display usable backlinks.
- The system visibly distinguishes canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion states.
- Imported content and AI suggestions cannot become canon without an explicit author action.
- Basic provenance distinguishes authored, imported, and AI-generated material.
- The author can search for and open scenes, characters, and locations.
- The application provides understandable hierarchy and relationship navigation.
- The supported AI capability is explicitly invoked, narrowly scoped, and produces reviewable AI suggestions without autonomous source changes.
- The author can export supported creative content in a documented, useful format.
- A backup can be created and verified.
- Restoration has been tested with representative data.
- A restored workspace retains essential hierarchy, content, states, supported links, backlinks, and provenance.
- Private content, credentials, and secrets are not committed to the repository.
- No Version 1 feature depends on modifying the old Story Engine or treating its story content as current canon.
- The core user journeys can be completed on supported desktop and laptop web browsers.

## Non-Goals

Version 1 is not intended to:

- act as an autonomous storyteller;
- replace the author’s creative judgment;
- treat AI output as authoritative;
- provide every feature of a full word processor;
- support teams, organizations, or collaborative editorial workflows;
- publish or publicly share creative work;
- model every possible story entity or relationship;
- perform comprehensive continuity reasoning;
- reproduce the old Story Engine;
- migrate all historical material automatically;
- become a general-purpose plugin platform;
- deliver every capability in the long-term product vision.

The goal is a dependable first workflow, not maximum feature breadth.

## Deferred Features

The following capabilities are explicitly out of scope for Version 1:

- maps and map generation;
- artwork generation and advanced asset management;
- NPC generators;
- city generators;
- creature generators;
- Google Docs integration;
- Google Drive integration;
- Gmail or other email workflows;
- publishing automation;
- EPUB production;
- print-layout production;
- real-time collaboration;
- public sharing;
- mobile-native applications;
- advanced story timeline analysis;
- advanced reader-reveal analysis;
- advanced character-knowledge analysis;
- migration of all Story Engine data;
- custom entity builders;
- plugin systems.

Deferral does not mean rejection. These features may be considered after the core workflow is working, secure, recoverable, and used in practice.

## Criteria for Moving a Deferred Feature Into Scope

A deferred feature may move into scope only when:

1. A real creative workflow demonstrates a recurring need for it.
2. The core Version 1 workflow is stable enough that the feature will not prevent completion of more fundamental work.
3. The feature has a clear, bounded user journey and acceptance criteria.
4. Its effect on authorial control, privacy, provenance, content states, export, backup, and restoration has been evaluated.
5. Its data and architecture requirements fit the established core model or justify an explicit durable decision.
6. Its security risks and external-service dependencies are understood.
7. It does not make an integration or proprietary format the sole custodian of the author’s work.
8. It can be implemented as a coherent capability rather than a partial collection of controls.
9. The expected creative value justifies its implementation and maintenance cost.
10. Moving it into scope is recorded in the product roadmap and any affected architecture or decision documentation.

Until those criteria are met and the scope change is explicitly approved, deferred features remain outside the release.
