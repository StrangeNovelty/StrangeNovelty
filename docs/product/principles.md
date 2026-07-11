# Strange Novelty Product Principles

These principles guide product, design, architecture, data, and implementation decisions for Strange Novelty. When features or technical choices conflict, prefer the option that best protects authorial control, clarity, privacy, and long-term ownership.

## 1. The Author Decides

AI and automation assist the creative process; they do not direct it.

The system may propose, summarize, organize, compare, or flag possible issues. It must leave creative judgment with the author. Important changes should be reviewable, understandable, and reversible.

No AI output becomes canon automatically.

## 2. Preserve Meaningful Distinctions

Canon, speculation, idea, draft, imported content, deprecated content, and AI suggestion are different states and must remain distinguishable.

The interface and data model should not blur these categories for convenience. Transitions between states should be intentional. Where a change affects creative authority—especially promotion to canon—the author should make or explicitly approve it.

The system should preserve provenance so the author can understand where material originated and how it reached its current state.

## 3. Treat Canon as Contextual

Canon is not necessarily global.

A statement may be true for one world, series, book, timeline, edition, point of view, or period while being false or unresolved elsewhere. Product design should avoid assuming that one universal truth applies across every creative context.

Conflicts should be surfaced for review, not silently resolved.

## 4. Separate Event, Reveal, and Knowledge

Story chronology, reader reveal chronology, and character knowledge are separate dimensions.

- Story chronology records when events happen in the fictional world.
- Reader reveal chronology records when the narrative discloses information.
- Character knowledge records what each character knows, believes, suspects, or misunderstands.

The system must not infer one solely from another. Tools that compare these dimensions should explain their reasoning and allow for intentional ambiguity, deception, nonlinear storytelling, and unreliable perspectives.

## 5. Make Connections Navigable

Links and backlinks are foundational, not optional decoration.

Every important piece of creative material should be able to connect to related material. Following a link should be easy, and linked items should reveal where they are referenced.

Use explicit connections to support context and discovery while avoiding unnecessary schema or forced categorization.

## 6. Keep AI Scope Deliberate

AI should receive only the context needed for the task at hand.

It must never blindly ingest an entire story directory. The author should be able to understand and control:

- which sources are included;
- which sources are excluded;
- why each source is relevant;
- whether private or imported material is involved;
- how the resulting output will be classified.

Prefer retrieval based on explicit selection, links, metadata, or a clearly described search over indiscriminate bulk ingestion.

## 7. Protect Privacy by Default

Strange Novelty is a private creative workspace. Privacy is a core product property, not an optional feature.

Minimize exposure of unpublished writing, artwork, research, credentials, personal information, and communications. Use conservative defaults for access, sharing, logging, integrations, and external AI services.

Private story files belong under `private-data/` and are never committed.

Security decisions should assume that creative material is valuable and sensitive even when it contains no conventional personal data.

## 8. Preserve Ownership and Exit Paths

The author owns the work and must be able to leave with it.

Data should be exportable in useful, documented formats. Backups must be practical to create, verify, and restore. Restoration should be treated as a product capability, not merely a storage implementation detail.

Avoid opaque storage or service dependencies that make migration impractical. Integrations may improve convenience, but no integration should become the sole custodian of the author’s work.

## 9. Import Without Assuming Authority

Imported material is evidence, not truth.

Content brought in from another application, document, archive, or integration should remain marked as imported until the author reviews it. An import process should preserve source information and avoid silently overwriting current work.

The old Story Engine is product-reference material only. Its product ideas and lessons may inform Strange Novelty, but its contents and implementation do not define the new system.

Story content inside the old application may be outdated and must not be treated as current canon.

## 10. Support Structure Without Imposing It

Strange Novelty supports multiple worlds, series, books, chapters, and scenes, but the product should remain flexible about how authors use them.

The hierarchy should provide orientation and organization without preventing cross-cutting links, shared material, alternate structures, or projects that do not use every level.

Prefer a clear default model with room for exceptions over either rigid enforcement or unlimited configuration.

## 11. Design for a Solo Creator

The primary user is one author and artist.

Optimize for focus, continuity, speed, trust, and low maintenance rather than organizational process or enterprise collaboration. Features should earn their place by improving the creator’s actual workflow.

Solo does not mean disposable. The system should still provide strong security, provenance, backups, recovery, and durable data ownership.

## 12. Keep the First Release Narrow

The first release must be small enough to finish, understand, and use.

Prioritize a coherent end-to-end workflow over a collection of partially developed features. Establish the core concepts—private storage, narrative organization, content states, links, controlled AI assistance, export, backup, and restoration—before expanding the product surface.

Defer features that do not materially improve the first usable workflow.

## 13. Grow Through Real Use

The long-term system may include writing, worldbuilding, maps, artwork, research, AI tools, Google Docs, Google Drive, email, publishing, NPC generation, city generation, and creature generation.

These possibilities are directions, not first-release requirements. Add capabilities in response to demonstrated creative needs, and integrate them through stable core concepts rather than one-off exceptions.

A feature should make the workspace more coherent, not merely larger.

## 14. Prefer Transparency and Reversibility

The author should be able to understand what the system did and recover from mistakes.

Important operations should expose their inputs, effects, and provenance. Destructive or authority-changing actions should require appropriate confirmation. Where practical, preserve history and provide undo, versioning, or restoration.

Automation that cannot explain its scope or be safely reversed should be treated with caution.

## 15. Favor Trustworthiness Over Cleverness

Strange Novelty should feel dependable.

Clear behavior, durable data, accurate status, and predictable navigation matter more than surprising automation. When uncertainty exists, the product should show that uncertainty rather than presenting an inference as fact.

The best system is one the author can trust with unfinished work.
