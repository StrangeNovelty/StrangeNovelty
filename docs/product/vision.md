# Strange Novelty Product Vision

## Overview

Strange Novelty is a private, secure, web-based creative workspace for a solo author and artist.

It provides one coherent place to develop stories, worlds, characters, chronology, artwork, research, and related creative material without surrendering authorial control. It should help the author understand connections, explore possibilities, maintain continuity, and move from ideas to finished work.

Strange Novelty is not an autonomous storyteller. AI assists; the author decides.

## Product Promise

Strange Novelty should help its author:

- organize multiple worlds, series, books, chapters, and scenes;
- write and revise long-form fiction;
- develop characters, places, cultures, events, creatures, and other worldbuilding material;
- distinguish established truth from drafts, possibilities, imports, and machine-generated suggestions;
- understand relationships through links and backlinks;
- reason about chronology, reader revelation, and character knowledge without conflating them;
- use AI selectively and transparently;
- keep creative work private, recoverable, and portable.

The workspace should reduce friction without flattening the creative process into a rigid database or allowing automation to take control of the work.

## Authorial Authority

The author is the final authority over every creative decision.

AI may summarize, compare, brainstorm, identify possible contradictions, suggest links, help organize material, or propose new content. It must not silently rewrite source material, promote its own output to canon, or obscure where an idea came from.

AI output never becomes canon automatically. It remains an AI suggestion until the author explicitly reviews and changes its status.

## Creative States and Provenance

Strange Novelty must preserve meaningful distinctions among content. At minimum, content may be identified as:

- **Canon** — accepted as currently true within the relevant story or world.
- **Speculation** — a possibility under consideration but not accepted as true.
- **Idea** — an undeveloped creative thought.
- **Draft** — authored material that is actively being written or revised.
- **Imported content** — material brought in from another source whose authority has not been established.
- **Deprecated content** — material intentionally retained for history or reference but no longer current.
- **AI suggestion** — machine-generated material that has not been accepted by the author.

These states must remain visible and distinguishable. The system should also preserve provenance where practical: who or what created the material, where it came from, when it changed, and whether the author has reviewed it.

Status is contextual. A fact may be canon in one world, series, book, timeline, or version without being universally true everywhere.

## Narrative Structure

Strange Novelty supports multiple creative projects and nested narrative structures, including:

- worlds;
- series;
- books;
- chapters;
- scenes.

The system should allow material to be shared where appropriate without assuming every project uses the same structure. A world may contain several series, a series may span several books, and a scene may connect to characters, places, events, research, artwork, and other story elements.

## Time, Revelation, and Knowledge

Strange Novelty must treat three related concepts separately:

1. **Story chronology** — when events happen within the fictional world.
2. **Reader reveal chronology** — when information is disclosed to the reader.
3. **Character knowledge** — what a particular character knows, believes, suspects, or misunderstands at a given point.

These concepts may influence one another, but they are not interchangeable. The system should make it possible to inspect and reason about each one independently.

A future continuity tool should be able to identify questions such as:

- Does an event occur before its cause?
- Has the reader learned a fact before a scene depends on it?
- Does a character act on information they could not yet know?
- Is a character’s belief intentionally false, outdated, or incomplete?

Such findings should be presented as reviewable observations, not automatic corrections.

## Links as a Foundation

Links and backlinks are a foundational product behavior.

Creative material rarely exists in isolation. A scene may reference a character, location, event, object, research source, image, or unresolved idea. Strange Novelty should make those connections explicit and navigable.

When one item links to another, the destination should expose the backlink. The author should be able to move through the creative workspace by following relationships as well as browsing a hierarchy.

Links should support discovery and context without forcing every relationship into a complicated schema.

## Privacy and Security

Strange Novelty is private by default.

The author’s unpublished writing, notes, artwork, research, and personal correspondence may be sensitive. Access controls, storage, integrations, logging, AI processing, exports, and backups must be designed with that sensitivity in mind.

Private story files belong under `private-data/` and are never committed to the repository.

AI should never blindly ingest an entire story directory. Every AI operation should use a deliberate, understandable scope. The author should be able to tell what material is being provided, why it is needed, and what result will be produced.

## Ownership and Durability

The author must retain ownership and control of the work.

Strange Novelty must support:

- export in useful, documented formats;
- backups that can be created and verified;
- restoration from backup;
- migration away from the product;
- recovery from mistakes or system failure.

The product must not make the author’s creative archive dependent on an opaque format or a single hosted service.

## Relationship to the Old Story Engine

The old Story Engine is product-reference material only.

Its workflows, interface ideas, implementation lessons, and product concepts may inform Strange Novelty. Its architecture and behavior should not be copied without review.

Story content found inside the old application may be incomplete or outdated. It must not be treated as current canon merely because it exists in that application or is imported from it. Any such material should enter Strange Novelty as imported content and remain clearly marked until the author reviews it.

## Long-Term Direction

Over time, Strange Novelty may grow into an integrated creative environment that includes:

- writing and revision;
- worldbuilding;
- maps;
- artwork and visual reference;
- research;
- AI-assisted creative and organizational tools;
- Google Docs integration;
- Google Drive integration;
- email integration;
- publishing workflows;
- NPC generation;
- city generation;
- creature generation.

This list describes a direction, not a commitment to build every capability or place it in the first release.

Integrations should extend the workspace without weakening privacy, ownership, provenance, or authorial control.

## First Release

The first release must stay narrow and usable.

Its purpose is to establish the core working model rather than anticipate the complete long-term system. It should focus on a small workflow that the author can use regularly and trust.

The first release should prioritize:

- a private workspace;
- basic organization across worlds, series, books, chapters, and scenes;
- clear content states;
- links and backlinks;
- deliberate AI assistance with visible scope and provenance;
- export, backup, and restoration fundamentals.

Features should be added only when they reinforce a real creative workflow. A smaller system that is clear, dependable, and pleasant to use is more valuable than a broad system whose core concepts are unfinished.
