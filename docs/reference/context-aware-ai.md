# Context-aware AI workspace

The AI Workspace extends the existing provider-neutral, reviewed Scene suggestion system. AI output is always non-authoritative: generation, acceptance as an interesting suggestion, and conversion into a native record are separate author-controlled actions. Existing Scene prose application continues to create immutable revisions and reject stale sources.

Context Packs are reusable Workspace-scoped selections with explicit typed links to story structure, Scenes and immutable revisions, Characters, Groups, abilities, world records, continuity and knowledge records, Timelines, Deck Draws, interpretations, and Cards. Assembly is deterministic and labeled. Objective truth, reader knowledge, Character knowledge, original Card text, and author Draw interpretation remain separate sections. A bounded context size produces visible truncation and omission notes.

Each creative request stores an immutable source identity snapshot, Scene revision identities, timestamps, assembly version, context hash, task key, provider/model identifiers, and provider usage metadata when available. Snapshots are not silently refreshed. Story Chat preserves each author and assistant message and links assistant responses back to the exact request and snapshot.

Task templates are versioned product behavior in code and contain no story material. They cover Chapter and Scene planning, Character and ability development, worldbuilding, Monster and NPC generation, continuity, chronology, Deck interpretation, Voice Profiles, and editorial review. Structured section validation prevents malformed output from being silently applied.

The optional OpenRouter adapter uses the non-streaming Chat Completions endpoint, bearer authentication from environment-only configuration, bounded timeout and output limits, normalized usage metadata, and privacy-safe error classifications. No provider credential is stored in the database, rendered HTML, logs, tests, or Git.

Model routing is task-based and environment-configurable. Writing, outlining, brainstorming, and analysis each have a model setting; writing may also have one alternate used only after a retryable provider failure. `AI_MODEL` remains the owner-controlled fallback. Every request records its routing category, configured primary model, models attempted, and actual returned model. A per-request override changes the model without changing the task's routing category.

Hosted configuration uses `AI_ENABLED`, `AI_ADAPTER`, `AI_OPENROUTER_API_KEY`, `AI_MODEL`, `AI_MODEL_WRITING`, `AI_MODEL_WRITING_ALTERNATE`, `AI_MODEL_OUTLINING`, `AI_MODEL_BRAINSTORMING`, `AI_MODEL_ANALYSIS`, `AI_TIMEOUT_SECONDS`, and `AI_MAX_OUTPUT_TOKENS`. Disable the provider with `AI_ENABLED=false`; change model choices through environment configuration without changing application code. The local deterministic fake remains available only in debug development and tests.
