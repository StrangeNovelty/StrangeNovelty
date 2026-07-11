# Old Story Engine Audit

## Purpose and Scope

This document audits the old Story Engine repository as read-only product and implementation reference for Strange Novelty. It evaluates observable structure, code, schemas, workflows, and user-facing behavior against the current Strange Novelty product and architecture documents.

The old repository is not a source of current Canon. Its story data, prompts, style material, screenshots, generated artifacts, and private assets were not copied into this audit. No database contents or secret values were inspected. The audit does not recommend retaining an implementation merely because it already exists.

Repository locations used for this audit:

- Strange Novelty: `/home/burmuss/projects/strange-novelty`
- old Story Engine: `/home/burmuss/projects/the-story-engine`

All old-repository paths cited below are relative to `/home/burmuss/projects/the-story-engine`. Line references describe the inspected revision and may move if that read-only repository changes.

## Audit Method

The audit used a bounded, static inspection. It did not launch the application, install dependencies, access external networks, execute migrations, open a database, inspect private story-bearing artifacts, or modify the old repository.

Inspected areas included:

- package and runtime manifests;
- Tauri configuration, capabilities, Rust entry points, commands, and embedded migrations;
- React routes, page and component structure, and selected workflow code;
- TypeScript database access functions and type definitions;
- import parsing, AI request construction, context assembly, search, export, snapshot, and auto-backup code;
- repository ignore rules, development scripts, and user/build documentation headings; and
- test-file and recovery-path presence.

Excluded from content inspection:

- SQLite databases or snapshots;
- screenshots and private visual assets;
- story-bearing Markdown, HTML, and JSON workflow payloads beyond filenames or structural role;
- generated `dist`, generated Tauri schemas, build output, dependency contents, and Git object contents; and
- any credential or personal-data value.

Findings use these labels:

- **Observed** — directly supported by inspected code, configuration, or repository structure.
- **Interpretation** — a reasoned implication of observed behavior.
- **Recommendation** — guidance for Strange Novelty, evaluated against its current requirements.

Absence means “not found in the bounded inspection,” not proof that a capability never existed outside the inspected revision.

## Repository Overview

### Observed

The old Story Engine is a single-repository desktop application. Its main areas are:

- `src/` — React user interface, workflows, browser-side database access, AI calls, import parsing, and backup scheduling;
- `src-tauri/` — Tauri desktop shell, SQLite migrations, filesystem-oriented backup/export commands, and capabilities;
- `notes/` — a user guide and build/session notes;
- `dist/` — generated frontend output;
- `node_modules/` and `src-tauri/target/` — installed and built dependencies/artifacts present locally;
- root-level screenshots, style material, workflow JSON, and a manual that appear story-bearing or private and were not inspected for content; and
- package, TypeScript, Vite, Tauri, and Rust manifests.

The root `README.md` remains the generic Tauri/React starter text rather than product or operating documentation (`README.md:1-7`). The repository ignore rules cover dependency, distribution, Rust build, generated-schema, and Windows metadata artifacts, but do not express the private-data boundaries required by Strange Novelty (`.gitignore:1-6`).

### Interpretation

The repository grew as a working personal application rather than from an explicit product, security, data, and recovery architecture. Code, story-specific behavior, migrations, and operations are concentrated in a small number of large files.

### Recommendation

Treat the repository as a catalog of workflow experiments and possible migration sources, not as a foundation to fork. Re-evaluate each concept against Strange Novelty’s narrower Version 1 scope.

## Observed Technology and Runtime Structure

### Observed

The frontend uses React, TypeScript, React Router, Vite, Tailwind tooling, D3, an icon library, and a document-parsing dependency. It runs inside Tauri 2. SQLite access is provided through the Tauri SQL plugin (`package.json`; `src-tauri/Cargo.toml`).

The native layer is a small Rust shell. It registers embedded forward migrations, filesystem commands, the opener plugin, and the SQLite plugin (`src-tauri/src/lib.rs:1-99`, `src-tauri/src/lib.rs:100-586`). Nearly all product and data-access logic is TypeScript in the webview.

The Tauri window is configured as a fixed desktop application. Its content security policy is explicitly null (`src-tauri/tauri.conf.json:11-23`). The main-window capability grants the webview SQL load, execute, select, and close permissions plus default opener permissions (`src-tauri/capabilities/default.json:1-13`).

### Interpretation

This is a local desktop trust model, not the server-enforced private web architecture selected conceptually for Strange Novelty. The webview combines presentation, data access, secret use, AI networking, and much domain logic. That coupling makes server-side authorization, narrow service authority, and independent security testing difficult to introduce incrementally.

### Recommendation

Do not assume Tauri, React, SQLite, or any listed dependency should be retained. Preserve only provider-independent workflow lessons. Strange Novelty technology choices require ADRs after the documented security, data, AI, integration, export, backup, and restoration constraints are satisfied.

## Application Entry Points

### Observed

The native executable calls the Tauri library entry point (`src-tauri/src/main.rs:1-6`). The Tauri configuration starts the Vite development server for development and builds the frontend for bundling (`src-tauri/tauri.conf.json:2-10`). The HTML shell loads `src/main.tsx`, which mounts the React application.

`src/App.tsx` is the main UI composition and route table. It starts auto-backup on application mount, loads a UI setting, installs a global search shortcut, renders the sidebar, and exposes routes for dashboard, characters, family, relationships, locations, story, plot threads, cross-reference, world, items, timeline, brainstorm, world bible, import, search, publication, voice profile, chat, and settings (`src/App.tsx:1-108`).

The development launch script assumes a Linux environment with a graphical display and a particular mounted drive arrangement, may invoke elevated directory/mount commands, and starts Tauri in development mode (`launch.sh:1-15`).

### Interpretation

The route breadth demonstrates many workflow experiments but also substantially exceeds Strange Novelty Version 1. Startup side effects, environment-specific mounting, and development-mode launch assumptions are not a suitable deployment contract.

### Recommendation

Use the route list as an inventory of past user needs. Do not reproduce it as initial scope. Version 1 should implement only the documented private writing workflow and its required recovery foundations.

## Major Modules and Responsibilities

### Observed

Major modules include:

- `src/App.tsx` and `src/components/Sidebar.tsx` — navigation and top-level application state;
- `src/db/database.ts` — approximately 2,500 lines of database connection, queries, mutations, domain interfaces, context assembly, search, and export-support access;
- `src-tauri/src/lib.rs` — native commands and all embedded schema migrations;
- `src/pages/Story/` — volume, arc, chapter, intake, outline, drafting, AI pipeline, snapshots, sliders, cross-references, and packaging workflows;
- `src/pages/Characters/`, `Locations/`, `Family/`, `World/`, and `Items/` — structured story-record management;
- `src/pages/Timeline/`, `PlotThreads/`, `WorldBible/`, `CrossReference/`, and `RelationshipWeb/` — knowledge, continuity, and navigation views;
- `src/pages/Brainstorm/`, `Chat/`, `VoiceProfile/`, and `components/AIAssistant.tsx` — several AI-assisted workflows;
- `src/lib/ai.ts` and `src/lib/agentContext.ts` — provider calls and context construction;
- `src/lib/importParser.ts` and `src/pages/Import/` — AI-based structured extraction, conflict review, and application;
- `src/lib/useAutoBackup.ts` and `src/pages/Settings/` — scheduled database copying, export, and recovery-facing controls; and
- `src/pages/Search/` backed by `searchGlobal` — application-wide text search.

### Interpretation

The module inventory captures valuable creative activities, but responsibilities are not cleanly separated. UI code can call the database and provider directly; provider-specific concepts appear across pages; data interfaces and query code share one large module; schema and native filesystem authority share one Rust file.

### Recommendation

Preserve conceptual boundaries rather than file structure: application-server domain services, typed repositories, a bounded AI gateway, staged imports, private object access, export/backup subsystems, and narrow job authority.

## Data-Storage Approach

### Observed

The application loads one local SQLite database named `storyengine.db` directly from TypeScript through the Tauri SQL plugin (`src/db/database.ts:1-10`). The database resides under the application configuration directory, inferred from the native backup commands (`src-tauri/src/lib.rs:5-23`).

Schema changes are embedded as a sequence of forward Tauri migrations in `src-tauri/src/lib.rs`. The inspected revision contains migrations for characters, relationships, settings, family records, locations, chapters, brainstorm sessions, world-bible entries, volumes, arcs, plot threads, timeline events, chapter links, publication, voice samples, items, chat, snapshots, writing statistics, and related records (`src-tauri/src/lib.rs:102-573`).

Most primary keys are SQLite auto-incrementing integers. Records generally lack a Workspace identifier, origin category, creative context, concurrency version, archive state, soft-deletion state, or generic provenance reference. Many foreign keys cascade hard deletion.

The `settings` table is an unrestricted key/value table (`src-tauri/src/lib.rs:145-148`). Application code stores UI preferences, AI configuration, style material, backup paths, and the external-service credential through the same database API (`src/db/database.ts:1108-1124`; `src/pages/Settings/index.tsx:50-128`).

### Interpretation

The database is a usable source inventory, but it is not compatible with the Strange Novelty authoritative model without transformation. Integer IDs are stable inside one surviving database, but there is no documented identity namespace across export, restore, re-import, or multiple Workspaces. Settings and credentials are insufficiently separated from creative data.

### Recommendation

Any future migration should read from a copy or documented export, assign or map stable Strange Novelty identifiers, preserve the old identifiers as external provenance, and stage every imported record. Do not import the old settings table wholesale.

## Content Hierarchy and Record Types

### Observed

The closest narrative hierarchy is Volume → Arc → Chapter. Volumes and arcs were added after the original chapter table, and chapter association is nullable (`src-tauri/src/lib.rs:419-435`). A Chapter contains brain dump, outline, draft, notes, status, number, and arc fields in one record (`src-tauri/src/lib.rs:312-329`). There are no distinct World, Series, Book, Chapter, and Scene records matching Strange Novelty Version 1.

Other record types include:

- Character and ability;
- Character relationship, progression, prediction, family, and personality data;
- Location, location event, connection, and prediction;
- world-bible entry;
- plot thread and timeline event;
- faction, codex entry, geography region, and item;
- brainstorm card and session;
- chapter intake, sliders, pipeline result, snapshot, publication, and link;
- voice sample; and
- chat session and message.

Several schemas encode story-specific taxonomies and fields directly, including fixed family roles, ability workflows, personality sliders, publication states, relationship kinds, and item/location categories.

### Interpretation

The breadth shows which structured concepts were useful in practice. It also tightly couples the database to one story and collapses multiple current concepts:

- a Chapter functions partly as Strange Novelty’s drafting Scene;
- record status fields mix lifecycle, story condition, workflow stage, publication state, and creative authority;
- Volume and Arc do not map cleanly to World, Series, Book, Chapter, and Scene;
- names and numbers are used heavily for organization and matching; and
- contextual Canon has no representation.

### Recommendation

Do not import tables one-for-one. Define a migration mapping per record family. Likely early candidates are old chapters as Imported content staged for later placement, characters, locations, and explicit relationship evidence. Story-specific extensions should remain deferred until demonstrated needs justify typed Strange Novelty records.

## Editing and Authoring Workflows

### Observed

The Story Workshop presents a staged chapter workflow that includes intake/context, brainstorming, outline, draft, automated review or generation passes, sliders, snapshots, and packaging. Draft and some metadata saves occur on blur or through explicit actions. Chapter updates write selected fields directly to the current row (`src/db/database.ts:907-928`; `src/pages/Story/ChapterDetail.tsx:184-536`).

Chapter snapshots store a full draft, word count, label, and creation time. They can be created before selected AI or restore operations and restored after first saving a “before restore” snapshot (`src/db/database.ts:2434-2465`; `src/pages/Story/ChapterDetail.tsx:394-414`). Snapshots can also be hard-deleted.

The application provides structured editors for characters, locations, world knowledge, timeline events, plot threads, and other specialized records. Several screens offer AI generation or analysis adjacent to editable authoritative fields.

### Interpretation

The progressive writing flow and pre-change snapshots are useful concepts. However, current-record updates have no base-version or stale-write detection, and snapshots are selective rather than a complete revision chain. AI-generated text can be applied into existing fields without a durable AI-suggestion state or uniform provenance boundary.

### Recommendation

Preserve the idea of visible writing stages, small focused forms, word-count feedback, and recovery before risky transformations. Rebuild editing on Scene identity, explicit revisions, concurrency checks, and separate AI suggestions. Do not copy the old automated generation pipeline into Version 1.

## Search and Navigation Behavior

### Observed

The application has sidebar navigation, direct record routes for some types, a keyboard shortcut for global search, cross-reference screens, a relationship visualization, and links between chapters and selected entities (`src/App.tsx:54-99`).

Global search performs case-insensitive SQL `LIKE` queries across many tables in parallel, caps results per type, builds text snippets, and returns routes for navigation (`src/db/database.ts:1893-2008`). Search includes potentially sensitive creative bodies such as draft, outline, notes, backstory, descriptions, and brainstorm notes, but it remains local to the desktop database in the inspected design.

### Interpretation

Cross-domain search and direct navigation are useful. The implementation is tightly bound to every table and returns heterogeneous routes, some of which lead to a general page rather than the exact result. It has no Workspace filter, state filter, Creative Context filter, provenance filter, or index consistency model.

### Recommendation

Preserve fast local-feeling search, useful snippets, keyboard access, and result-type labels. Reimplement against Strange Novelty’s supported Scene, Character, and Location fields with Workspace authorization, state/provenance filters, stable record routes, and privacy-conscious logging.

## Linking and Relationship Behavior

### Observed

The old system has several relationship representations:

- Character-to-Character relationships with type, label, and description (`src/types/index.ts:29-67`);
- Chapter-to-Character and Chapter-to-Location junction tables (`src-tauri/src/lib.rs:331-345`);
- Location connections;
- faction membership and family-specific links;
- plot-thread opening and resolution chapter references;
- timeline event references; and
- directional Chapter links with a small relationship vocabulary (`src-tauri/src/lib.rs:449-453`).

Character relationship queries explicitly retrieve either endpoint, which provides a reverse view for that one relationship type (`src/db/database.ts:133-158`). Chapter-character and chapter-location queries support navigation in both directions (`src/db/database.ts:930-985`).

### Interpretation

Bidirectional navigation and small typed relationship vocabularies remain useful. The implementation has multiple unrelated relationship systems, no common Link identity model, incomplete endpoint coverage, no Workspace boundary, and mostly hard-cascade deletion. Backlinks are page-specific queries rather than a defined derived view of one authoritative Link record.

### Recommendation

Use old relationships and junction rows as candidate imported relationship evidence. Map only supported Scene, Character, and Location endpoints into staged Strange Novelty Links. Do not carry over unsupported relationship types or infer authority from the old graph.

## Import and Export Behavior

### Import observations

The import page accepts raw text, sends it to the configured AI provider for structured extraction, parses returned JSON, detects possible conflicts, presents a review UI, and applies selected changes (`src/pages/Import/index.tsx`; `src/lib/importParser.ts:120-348`).

Characters and Locations are matched by lowercased name. Empty existing fields are proposed as automatic fills; differing fields become conflicts whose default choice is to keep the existing value. New records and relationships are proposed. Application runs item by item, catches individual errors, and can partially succeed without a surrounding transaction (`src/lib/importParser.ts:163-276`).

Imported records are written directly into the same tables and status model as existing records. The code does not create an Import Batch, imported provenance, Imported content state, source manifest, retained transformation record, or durable review event.

### Export observations

The Settings page creates:

- a human-readable HTML story-bible export;
- a versioned JSON export described in the UI as a recovery format; and
- chapter-level plain-text files (`src/pages/Settings/index.tsx:158-190`, `src/pages/Story/ChapterDetail.tsx:1994-2023`).

The JSON builder exports many major tables and selected child records with numeric identifiers (`src/pages/Settings/index.tsx:669-745`). It does not include every migrated table visible in the schema. Notably, the inspected builder does not show complete inclusion of snapshots, chat, pipeline results, chapter links, settings, items, all relationship families, all private artifacts, or a manifest and integrity record.

### Interpretation

The conflict-review interaction and readable export are valuable. The import’s provider exposure, name-based identity, direct authoritative writes, partial application, and missing provenance conflict with Strange Novelty. The JSON export is useful as a candidate migration source but should not be assumed complete or safely restorable merely because the UI labels it a recovery format.

### Recommendation

Preserve staged preview and per-field conflict review. Replace AI-first import parsing with a bounded, format-specific, untrusted-input pipeline where possible. Treat every old JSON export as untrusted, possibly incomplete Imported content; verify structure, preserve source identifiers, and never infer Canon.

## Authentication and Privacy Behavior

### Observed

No sign-in, owner enrollment, session, authorization, or Workspace ownership layer was found. Routes render directly, and TypeScript functions execute database reads and writes from the Tauri webview (`src/App.tsx:65-107`; `src/db/database.ts:1-49`).

The old application is packaged as a local desktop app rather than a publicly hosted web application. That reduces some network exposure but makes operating-system account, device, filesystem, desktop shell, and webview security the practical privacy boundary.

The webview capability permits SQL select and execute access, and the Tauri configuration has no CSP (`src-tauri/capabilities/default.json:1-13`; `src-tauri/tauri.conf.json:11-23`). Native commands expose database copying, export writing, backup listing/pruning, directory disclosure, and copying to a caller-provided destination (`src-tauri/src/lib.rs:5-98`).

### Interpretation

The old design relies substantially on local-device and browser/webview trust. It does not meet Strange Novelty’s requirement that only the authenticated owner may access content and that authentication, authorization, validation, and storage mediation occur server-side. A webview compromise would have broad database and local command authority.

### Recommendation

Do not reuse the old trust model, Tauri capabilities, or browser-side repository layer. Strange Novelty must establish server-enforced identity and authorization for every private operation and narrow authority for jobs, storage, AI, imports, exports, and restoration.

## AI or External-Service Behavior

### Observed

The application sends chat-completion requests directly from frontend TypeScript to one configured external API endpoint using a bearer credential loaded from local settings (`src/lib/ai.ts:1-82`). Provider and model choices are embedded in frontend code.

AI appears in multiple workflows: a character assistant, chapter generation and review passes, voice profiling, family and location suggestions, brainstorming, chat, context filtering, and import extraction. Some results are stored in dedicated result or chat tables, while other workflows apply generated material to authoritative fields.

Context construction includes:

- character backstory snippets for the assistant;
- chapter-linked Characters, Locations, abilities, stages, and relationships;
- world-bible and world-structure strings;
- timeline/reveal-derived context; and
- a provider-assisted filter for factions, codex entries, and regions.

When the provider-assisted world-context filter fails, it falls back to returning all records in those categories. A character-presence helper similarly falls back to all Characters when no name match is found (`src/lib/agentContext.ts:39-100`).

### Interpretation

The old system demonstrates task prompts, visible usage in one chat workflow, linked-record context, and a rudimentary reveal concept. It does not provide the required single bounded Version 1 capability, context manifest, reliable preview, uniform explicit invocation boundary, state separation, or provider isolation. Failure paths can broaden context. Story text and import input can influence prompts without a documented prompt-injection boundary. Credentials and provider calls occur in the client.

### Recommendation

Do not reuse provider configuration, prompt bodies, hardcoded model lists, direct-fetch code, bulk context fallbacks, or autonomous generation passes. Preserve only the ideas of explicit task buttons, linked context candidates, source-aware context, usage visibility, and keeping provider failure from blocking ordinary work. Implement the selected scene-focused review through the Strange Novelty AI gateway and manifest rules.

## Configuration and Secret Handling

### Observed

The external-service credential is entered through Settings, stored as a value in the SQLite `settings` table, loaded into React state, and passed to browser-side `fetch` (`src/pages/Settings/index.tsx:50-85`; `src/components/AIAssistant.tsx:23-68`; `src/lib/ai.ts:43-62`). The same table stores non-secret preferences and potentially sensitive author style/context material.

No dedicated secret store, credential encryption, rotation workflow, redaction boundary, environment separation, or revocation workflow was found. The Git inspection found no tracked file whose name clearly indicated a database, environment-secret file, credential, or backup, but filename checks cannot prove that repository history or arbitrary files contain no secrets.

The configured cloud-backup destination is a local path, and the launch script assumes a particular mounted drive (`src/lib/useAutoBackup.ts:7-19`; `launch.sh:9-15`).

### Interpretation

The old credential is exposed to the webview and stored alongside ordinary application data. A raw database backup likely includes it because backup copies the whole database file. This conflicts directly with Strange Novelty’s secret isolation and backup rules.

### Recommendation

Exclude all old settings and credentials from migration and exports. Never read or reproduce existing secret values during audit or migration. Require the author to configure fresh credentials through the future server-side secret-management design and revoke old credentials separately.

## Logging and Error Handling

### Observed

Error handling is primarily local UI state, `alert`, `console.warn`, and `console.error`. Several catches convert provider, filesystem, database, or import errors directly to strings for display. Import application collects per-item error messages; backup operations report paths and copy failures; provider errors may be returned from the remote response and displayed (`src/lib/importParser.ts:268-348`; `src/lib/useAutoBackup.ts:7-19`; `src/lib/ai.ts:64-67`).

No structured operational logging, audit-event model, redaction policy, telemetry boundary, log retention, security-event review, or incident workflow was found. The local desktop structure may mean console output is transient, but the code does not enforce privacy-conscious error shaping.

### Interpretation

Simple visible errors are useful for a personal tool, but arbitrary error strings can expose provider details, local paths, SQL or content context. There is no durable distinction between authority-related audit records and operational diagnostics.

### Recommendation

Preserve clear, actionable user-facing failure states. Replace arbitrary error propagation with bounded categories and correlation identifiers. Implement separate protected audit records and privacy-conscious operational logs as defined by the Strange Novelty security architecture.

## Backup, Recovery, and Migration Behavior

### Observed

The native backup command copies the live SQLite file into a `backups` directory under application configuration and names it with a Unix timestamp. A pruning command retains a caller-specified number of matching database files. Auto-backup can run on launch and at fixed intervals, retaining fifteen database copies (`src-tauri/src/lib.rs:5-76`; `src/lib/useAutoBackup.ts:5-55`).

A configured destination path can receive a second filesystem copy. The copy is described as cloud backup but is implemented as a local path copy and relies on external mounting or synchronization outside the application (`src-tauri/src/lib.rs:88-98`; `src/pages/Settings/index.tsx:127-149`).

The Settings UI instructs the user to restore a database by replacing the main file and describes JSON as readable/restorable, but no in-application database restore, JSON restore, integrity verification, backup manifest, checksum, isolated restoration, compatibility validation, or representative restoration test was found (`src/pages/Settings/index.tsx:458`, `src/pages/Settings/index.tsx:527`).

Schema migrations are forward `Up` migrations embedded in the application. One migration deletes duplicate world-bible rows before enforcing a unique index (`src-tauri/src/lib.rs:390-417`). No rollback migration set or migration recovery procedure was observed.

### Interpretation

Automated local copies and visible retention are useful concepts, but direct copying of a live database is not proven to create a consistent backup. Backups may contain the provider credential. They share a nearby failure domain by default, lack integrity evidence, and have no tested restoration contract. The data-deleting migration illustrates why migrations require verified recovery points and explicit transformation reporting.

### Recommendation

Do not reuse the backup commands or restoration instructions. Preserve scheduled backup, visible status, retention, and a separate-copy concept. Strange Novelty must define complete contents, exclude live secrets, create manifests and integrity data, verify referenced objects, isolate restoration, migrate deterministically, and pass a representative restoration test.

## Testing and Development Tooling

### Observed

The package scripts provide development, TypeScript-plus-Vite build, preview, and Tauri commands (`package.json`). No unit, integration, end-to-end, security, migration, export, backup, or restoration test files or test runner configuration were found outside installed/generated directories.

TypeScript configuration, package lockfiles, Rust lockfiles, and build manifests support reproducible dependency resolution to a degree. The inspected repository also contains installed dependencies and generated/build output locally, although ignore rules cover the principal directories.

The generic root README and environment-specific launch script are the primary top-level development instructions. The user guide and session log document workflows and known behavior, but parts are story-specific and were not used as current requirements.

### Interpretation

Build tooling exists, but verification is predominantly manual. The absence of automated tests is especially risky around a 2,500-line database module, destructive cascades, AI parsing, partial imports, backup copying, and migrations.

### Recommendation

Do not carry forward “build succeeds” as sufficient verification. Strange Novelty needs automated domain, authorization, concurrency, import, AI-boundary, export, backup, migration, restoration, and privacy tests before accepting corresponding capabilities.

## Deployment Assumptions

### Observed

The application assumes a single local desktop user, local SQLite, a Tauri webview, outbound provider access, and filesystem access under the application configuration directory. The launch script specifically assumes a graphical Linux/WSL-like environment and an optionally mounted drive used as a copy destination (`launch.sh:1-15`).

The Vite development server uses a fixed port and can take a host from an environment variable (`vite.config.ts:5-30`). No hosted production server, reverse proxy, TLS termination, authentication service, centralized secret service, monitoring platform, or remote database is defined.

### Interpretation

The desktop deployment may have served a single-machine workflow well, but it does not answer Strange Novelty’s private-web deployment, network exposure, authenticated access, administrative access, browser boundary, or multi-device questions.

### Recommendation

Treat deployment as undecided. Record the future Strange Novelty deployment and trust-boundary choice in an ADR; do not infer it from the old application or its environment-specific launcher.

## Useful Concepts Worth Preserving

These are conceptual candidates, not approval to copy code or schemas:

- a staged authoring flow from raw thoughts through outline and draft;
- a focused writing surface with word count and explicit packaging/export actions;
- snapshots before risky replacement or AI-assisted transformation;
- Characters and Locations as navigable structured records;
- explicit Chapter-to-Character and Chapter-to-Location associations;
- visible relationships and reverse navigation;
- global search across narrative and structured content with snippets and shortcuts;
- timeline events, plot threads, secrets/reveal hints, and cross-reference views as evidence of future needs;
- import preview with per-field conflict choices and default preservation of existing values;
- readable HTML and plain-text exports in addition to structured export;
- visible backup controls, automated schedules, bounded retention, and a separate-copy option;
- AI invoked from a concrete creative workflow rather than as an invisible background process;
- source-aware AI context assembled from linked records; and
- visible provider usage counts where available.

Each concept must be narrowed to the current product phase. Timeline, publication, advanced worldbuilding, generators, general chat, and integrations remain outside Version 1 even if they were useful before.

## Useful Implementation Patterns Worth Reconsidering

The following patterns solved real problems but should be redesigned rather than copied:

| Old pattern | Useful intent | Why reconsider it |
| --- | --- | --- |
| SQLite migrations embedded in the Tauri entry file | Keep schema evolution with the application | Couples native startup, schema, and product code; includes destructive transformation without documented recovery |
| One TypeScript database module | Centralize queries | Too large; mixes types, persistence, search, context, and domain behavior; runs in the webview |
| Junction tables for chapter participation | Represent explicit relationships | Missing Workspace ownership, Link identity, provenance, lifecycle, and uniform backlinks |
| Direct field updates | Simple editing | No concurrency token, complete revision chain, or authority-transition boundary |
| Chapter snapshots | Recover before replacement | Selective and hard-deletable; not a general revision model |
| Name-based import matching | Find likely duplicates | Names are not identity; risks false merges and lacks source mapping |
| Per-field conflict review | Preserve author choice | Apply is non-transactional and imported state/provenance are lost |
| Provider-assisted context filtering | Reduce context size | Provider receives discovery input; failure broadens to all candidates |
| Settings-table credential storage | Simple local configuration | Secret is exposed to webview and likely included in raw database backups |
| Live database file copy | Easy backup | Consistency, integrity, credential exclusion, and restoration are unverified |
| JSON “recovery” export | Portable structured copy | Coverage is incomplete and no importer or restoration test was found |
| Direct filesystem Tauri commands | Enable export and backup | Webview receives broad path and file authority without the new server boundary |

## Known Limitations and Risks

### Data and integrity

- No Workspace ownership field or cross-Workspace protection.
- Auto-increment identities lack a documented portable namespace.
- Hard deletes and cascade deletes remove content and relationships without trash or retained deletion history.
- Update functions accept dynamic field maps and have no concurrency version.
- Revision history is limited to selected Chapter snapshots.
- Import application can partially succeed and is not shown as transactional.
- The structured export does not cover every schema area.
- Backup consistency and restoration are not verified.

### Security and privacy

- No application authentication or authorization layer.
- Webview code has direct SQL read/write capability.
- CSP is disabled in the Tauri configuration.
- Provider credentials are stored in the application database and loaded client-side.
- Provider requests originate from client code.
- Native commands accept filesystem paths or filenames from the webview; their safety was not established by tests.
- Errors may expose provider details or local paths.
- Database backups likely include settings and credentials.

### Product and authority

- Required Strange Novelty creative states are absent.
- Contextual Canon is absent.
- Imported and AI-generated origins are not durably preserved.
- Several AI outputs can move directly into authoritative fields.
- Story chronology, reader reveal, and character knowledge are not cleanly separated.
- Schemas and prompt logic contain story-specific assumptions.
- The product surface is much broader than Strange Novelty Version 1.

### Maintainability and operations

- Core persistence logic is concentrated in a very large frontend file.
- Provider-specific AI behavior is duplicated across multiple pages.
- No automated test suite was found.
- Root documentation remains mostly template text.
- Development and backup assumptions depend on a particular local environment.
- Installed dependencies and build artifacts increase local repository noise, even where ignored.

## Conflicts with Current Strange Novelty Requirements

| Strange Novelty requirement | Old Story Engine observation | Assessment |
| --- | --- | --- |
| Private authenticated owner access | Local desktop routes and direct webview database access; no auth/session layer found | Conflicts |
| Server-side authentication and authorization | No application server policy boundary | Conflicts |
| Explicit Workspace ownership | No Workspace identifier in inspected schemas | Conflicts |
| World → Series → Book → Chapter → Scene | Volume → Arc → Chapter; draft stored on Chapter | Conflicts; requires deliberate mapping |
| Stable portable identity | Local integer IDs with no documented namespace or restore mapping | Insufficient |
| Required creative states | Domain-specific statuses only | Conflicts |
| Contextual Canon | No explicit representation | Conflicts |
| Durable provenance | Origin and authority history generally absent | Conflicts |
| Scene revisions and stale-write detection | Selective Chapter snapshots; no concurrency version | Insufficient |
| Typed Links with dependable backlinks | Several unrelated junction and relationship tables | Partially useful, structurally incompatible |
| Recoverable deletion | Direct deletes and cascading foreign keys | Conflicts |
| Staged imports with Imported content state | AI parse and review followed by direct writes | Conflicts |
| One bounded scene-focused AI capability | Multiple chat, generation, analysis, filtering, and import operations | Conflicts with Version 1 scope |
| Context manifest and preview | Ad hoc prompt construction; no manifest found | Conflicts |
| Imported and legacy excluded by default | No origin model; broad fallback context exists | Conflicts |
| Provider isolation and server-side credentials | Client fetch with key loaded into webview | Conflicts |
| Privacy-conscious logs and errors | Console and raw error-string patterns | Insufficient |
| Complete documented export | Multiple useful exports, but structured coverage appears incomplete | Insufficient |
| Verified backup and tested restoration | Raw copies and instructions; no integrity or restoration test found | Conflicts |
| Version 1 usable without external integrations | Core local editing exists, but several workflows depend on AI | Partially aligned; AI-dependent workflows must not define the core |

## Material Explicitly Excluded from Reuse

The following must not be copied into Strange Novelty as implementation, configuration, seed data, prompts, or Canon:

- any old manuscript, story note, world-bible text, character biography, location description, chapter draft, brainstorm result, chat, or research content;
- the contents of the old SQLite database, backups, or exports except through a future approved import workflow;
- screenshots, artwork, private visual assets, and personal files;
- style guides, forbidden-word lists, story-specific AI instructions, or prompt bodies;
- bundled workflow JSON and automation recipes without independent security, privacy, rights, and product review;
- credentials, tokens, settings-table secret values, local paths, or environment-specific configuration;
- hardcoded story-specific taxonomies, family assumptions, abilities, seed records, and domain rules;
- provider lists, endpoint choices, model defaults, and direct client-side request code;
- the disabled CSP and broad webview SQL/filesystem authority;
- name-based identity and automatic merge assumptions;
- raw database copying as the Strange Novelty backup design;
- any claim that old content is current Canon because it existed in the application; and
- old generated output, installed dependencies, build artifacts, or distribution files.

The old repository itself remains read-only and must never be modified by Strange Novelty work.

## Candidate Migration Inputs

The following may be evaluated later as untrusted import sources. None is approved for migration or Canon status now.

### Structured JSON exports

Potentially useful because they expose version, local identifiers, major record groups, and selected relationships. Risks include incomplete coverage, no integrity manifest, schema drift, embedded private content, and missing provenance/state semantics.

### A read-only copy of the SQLite database

Potentially the most complete structural source. It must never be opened in place or copied into the repository. A future importer would need schema-version detection, secret/settings exclusion, integrity checks, stable external-ID mapping, per-table validation, and a staging report.

### Human-readable HTML and plain-text exports

Useful for author inspection and fallback recovery. They are weaker structured sources and may contain sensitive manuscripts. Import would require explicit file selection and Imported content provenance.

### Selected structural records

Characters, Locations, Chapters, Chapter associations, relationships, timeline events, plot threads, and world-bible entries may provide evidence for future import. Only types in approved Strange Novelty scope should be mapped initially; others should remain staged or deferred.

### Legacy identifiers and timestamps

Old table name, numeric ID, export version, and available timestamps can support provenance and duplicate review. They must not become Strange Novelty primary identity or prove authority.

### Migration rules

Any future migration must:

- use an explicit, narrow source chosen by the author;
- avoid reading unrelated private files or the live old application directory;
- exclude settings and secret-bearing configuration;
- validate untrusted content and format limits;
- create an Import Batch and stable source mappings;
- assign Imported content state and imported provenance;
- preserve old identifiers only as external references;
- avoid name-based automatic merges;
- show unresolved mappings and partial failures;
- require explicit author review before authoritative acceptance;
- never promote content to Canon automatically; and
- be covered by export, backup, restoration, migration, privacy, and security tests.

## Questions Requiring Later Investigation

1. Which old repository revision and database schema version represent the author’s last usable state?
2. Does a safe, author-approved structured export exist, and which record groups does it actually contain?
3. Are there multiple databases or backup generations, and which are intact without opening them during planning?
4. Can SQLite backup consistency be established for existing copies before any migration attempt?
5. Which old Chapters represent books, chapters, scenes, fragments, or generated drafts in the new hierarchy?
6. How should Volume and Arc map, if at all, to World, Series, Book, Chapter, and Scene?
7. Which Character and Location records remain relevant enough for the author to select for import?
8. Which old relationship kinds can map to supported Strange Novelty Links without changing meaning?
9. Which records are duplicates created through imports, seeding, or name variation?
10. Are timestamps reliable enough to support ordering or provenance, and what timezone assumptions were used?
11. Which Chapter snapshots are meaningful revision evidence, and are their parent drafts present?
12. Which old status fields describe lifecycle, workflow, fictional condition, publication, or creative authority?
13. Can imported AI output be distinguished from author-written content anywhere beyond table or field location?
14. Which imports originated from external documents, and is source information recoverable without exposing the documents during planning?
15. Which export fields or tables are omitted from the versioned JSON builder in the actual last-used revision?
16. Were any backups ever restored successfully, and is there evidence beyond user instructions?
17. Do old backups contain credentials or other settings that must be stripped before secure handling?
18. Are any external copies on mounted or synchronized storage still retained, and what privacy controls apply?
19. Which old workflows were used repeatedly versus implemented speculatively?
20. Which concepts should remain deferred because they exceed Version 1 even if their old data exists?
21. What synthetic fixture can represent the old schema for importer tests without using private content?
22. Which migration decisions require ADRs before any importer is implemented?

These questions should be investigated only when a bounded migration or product decision requires them. Private artifacts must not be ingested merely to make the audit more complete.

## Summary Recommendations

1. **Do not fork or modernize the old application.** Its desktop/webview trust model, direct client database access, broad scope, and coupled modules conflict with Strange Novelty’s documented architecture.
2. **Preserve workflow lessons, not implementation authority.** The staged writing flow, search, explicit relationships, snapshots, import conflict review, readable exports, and visible backup controls are the strongest reusable concepts.
3. **Leave broad automation behind for Version 1.** General chat, generation pipelines, AI parsing, world-wide context fallbacks, publication, large entity breadth, and story-specific generators exceed the current scope and weaken context control.
4. **Treat all old data as imported evidence.** No old record, status, prompt, or relationship is current Canon by existence. A future importer must stage, validate, map identity, preserve provenance, and require author review.
5. **Never migrate configuration wholesale.** Exclude settings, credentials, tokens, paths, provider configuration, and secret-bearing backups. Configure new services independently and server-side.
6. **Design migration around the new model.** Map only approved types into Workspace-owned stable identities, explicit content states, contextual Canon, revisions, Links, lifecycle history, and provenance.
7. **Build recovery before migration.** Strange Novelty export, verified backup, isolated restoration, and migration rules should be operational before importing valuable legacy material.
8. **Use synthetic tests first.** Reproduce only the old schema shape needed for importer tests, not private story contents. Test duplicates, partial data, malformed records, old versions, name collisions, and interrupted migration.
9. **Keep the old repository immutable.** Work from approved copies or exports when migration is later authorized, and preserve the original as reference evidence.
10. **Make each retained idea earn its place.** Current product principles, Version 1 scope, security invariants, AI context rules, and portability requirements take precedence over old behavior.
