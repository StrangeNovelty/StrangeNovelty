# Context-aware AI workspace

The AI Workspace extends the existing provider-neutral, reviewed Scene suggestion system. AI output is always non-authoritative: generation, acceptance as an interesting suggestion, and conversion into a native record are separate author-controlled actions. Existing Scene prose application continues to create immutable revisions and reject stale sources.

Context Packs are reusable Workspace-scoped selections with explicit typed links to story structure, Scenes and immutable revisions, Characters, Groups, abilities, world records, continuity and knowledge records, Timelines, Deck Draws, interpretations, and Cards. Assembly is deterministic and labeled. Objective truth, reader knowledge, Character knowledge, original Card text, and author Draw interpretation remain separate sections. A bounded context size produces visible truncation and omission notes.

Each creative request stores an immutable source identity snapshot, Scene revision identities, timestamps, assembly version, context hash, task key, provider/model identifiers, and provider usage metadata when available. Snapshots are not silently refreshed. Story Chat preserves each author and assistant message and links assistant responses back to the exact request and snapshot.

Task templates are versioned product behavior in code and contain no story material. They cover Chapter and Scene planning, Character and ability development, worldbuilding, Monster and NPC generation, continuity, chronology, Deck interpretation, Voice Profiles, and editorial review. Structured section validation prevents malformed output from being silently applied.

The optional OpenRouter adapter uses the non-streaming Chat Completions endpoint, bearer authentication from environment-only configuration, a configurable model identifier, timeout, output limit, normalized usage metadata, and privacy-safe error classifications. No provider credential is stored in the database, rendered HTML, logs, tests, or Git.
