# ADR-0016: Story Engine Workflow Fidelity

- **Status:** Accepted
- **Decision date:** 2026-07-18
- **Decision owner:** Repository owner

## Context

Strange Novelty has expanded the original desktop Story Engine into a private, hosted creative system. That expansion preserved more structured data and stronger provenance, but it also distributed several proven creative workflows across separate libraries and tools. The result can be capable while still making the author's next action difficult to see.

The desktop application's story data is not authoritative Strange Novelty content, and its local trust model is not suitable for the hosted application. Its product organization and creative workflow, however, have been explicitly selected as the binding behavioral reference.

## Decision

The desktop Story Engine defines the required workflow organization for the corresponding Strange Novelty capabilities:

- its grouped creative navigation informs the web shell;
- Brainstorm remains one world-aware workspace with generator modes and persistent sessions;
- reviewed generated material exposes an obvious, universal Apply to Story path;
- the Chapter experience presents one continuous planning, drafting, editorial, linking, packaging, and publication pipeline;
- World Bible and structured world records operate as complementary views;
- Character identity, personality, relationships, family, abilities, appearances, and creative tools form one dossier workflow; and
- contextual guidance explains where information belongs and how it returns to the story.

Web-native improvements remain authoritative constraints: Workspace authorization, PostgreSQL persistence, immutable Scene revisions, private hosted storage, review-first AI, explicit provenance, typed continuity and chronology, research, and publication history. Fidelity restores organization and behavior; it does not copy the desktop runtime, local database, private content, secrets, or unsafe mutation patterns.

## Consequences

- Product reviews compare shared workflows against the desktop behavior before inventing new organization.
- Expanded web capabilities must support the central creative path instead of obscuring it.
- Desktop prompts may be studied privately for behavioral requirements, but private or story-specific wording is not committed.
- Desktop data never becomes Canon merely because the desktop application displayed it.
- Visual fidelity is demonstrated with rendered comparisons while preserving accessible, responsive web behavior.

## Superseded guidance

Earlier documentation that described the desktop application only as an optional catalog of ideas is narrowed by this decision. It remains non-authoritative for architecture, security, operations, and story data, but is binding for corresponding product workflows.
