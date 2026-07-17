from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AITask:
    key: str
    title: str
    category: str
    description: str
    output_sections: tuple[str, ...]
    conversion_targets: tuple[str, ...] = ()


def task(key, title, category, sections, targets=()):
    return AITask(
        key,
        title,
        category,
        f"Use deliberately selected context to {title.lower()}.",
        tuple(sections),
        tuple(targets),
    )


TASKS = {
    item.key: item
    for item in (
        task(
            "story_chat", "Continue Story Chat", "chat", ("Response", "Questions", "Possibilities")
        ),
        task(
            "chapter_directions",
            "Brainstorm Chapter Directions",
            "chapter",
            ("Current Story Position", "Three Directions", "Tradeoffs", "Continuity Opportunities"),
            ("chapter", "plot_thread"),
        ),
        task(
            "chapter_outline",
            "Build Chapter Outline",
            "chapter",
            ("Chapter Function", "Key Beats", "Scene Breakdown", "Emotional Arc", "Ending Hook"),
            ("chapter_outline",),
        ),
        task(
            "chapter_continuity",
            "What Can Pay Off Here?",
            "chapter",
            ("Relevant Open Threads", "Payoff Opportunities", "Risks", "Questions"),
            ("plot_thread", "clue", "reveal"),
        ),
        task(
            "scene_brief",
            "Build Scene Brief",
            "scene",
            (
                "Scene Function",
                "POV",
                "Character Wants",
                "Main Conflict",
                "Stakes",
                "Setting and Atmosphere",
                "Blocking and Beats",
                "Emotional Movement",
                "Continuity Risks",
                "Opening Beat",
                "Ending Hook",
            ),
        ),
        task(
            "scene_revision",
            "Revision Suggestions",
            "scene",
            ("Source Excerpt", "Concern", "Importance", "Explanation", "Proposed Revision"),
            ("scene_revision",),
        ),
        task(
            "scene_rewrite",
            "Rewrite with Constraints",
            "scene",
            ("Original", "Proposed Text", "Constraint Notes"),
            ("scene_revision",),
        ),
        task(
            "character_deepen",
            "Deepen Character",
            "character",
            (
                "Motivations",
                "Internal Conflict",
                "Contradictions",
                "Relationships",
                "Arc Possibilities",
                "Questions",
            ),
            ("character", "plot_thread"),
        ),
        task(
            "character_knowledge",
            "What Does This Character Know?",
            "character",
            ("Objective Truth", "Known", "Suspected", "Mistaken Beliefs", "Hidden From Them"),
            ("knowledge",),
        ),
        task(
            "ability_next",
            "Suggest Next Progression Stage",
            "ability",
            (
                "Plausible Stage",
                "Catalyst",
                "Training",
                "Costs",
                "Limitations",
                "Failure Modes",
                "Counters",
                "Narrative Consequences",
                "Endgame Possibilities",
            ),
            ("ability_stage", "ability_event"),
        ),
        task(
            "ability_consistency",
            "Progression Consistency Review",
            "ability",
            (
                "Current Rules",
                "Consistent Elements",
                "Possible Conflicts",
                "Questions",
                "Suggestions",
            ),
        ),
        task(
            "location_develop",
            "Develop Location",
            "world",
            (
                "Identity",
                "History",
                "Atmosphere",
                "Sensory Detail",
                "Hazards",
                "Current State",
                "Story Uses",
            ),
            ("location",),
        ),
        task(
            "region_develop",
            "Develop Region",
            "world",
            ("Geography", "Culture", "Politics", "Conflicts", "Travel", "Historical Layers"),
            ("region",),
        ),
        task(
            "group_develop",
            "Develop Group or Faction",
            "world",
            (
                "Goals",
                "Hidden Goals",
                "Resources",
                "Methods",
                "Internal Structure",
                "Alliances",
                "Enemies",
                "Conflict Possibilities",
            ),
            ("group",),
        ),
        task(
            "codex_develop",
            "Develop Codex Concept",
            "world",
            ("Definition", "Implications", "Related Terms", "Continuity Questions"),
            ("codex",),
        ),
        task(
            "item_generate",
            "Design Item or Artifact",
            "world",
            (
                "Name Options",
                "Origin",
                "Function",
                "Capabilities",
                "Costs",
                "Dangers",
                "Ownership History",
                "Story Importance",
            ),
            ("item",),
        ),
        task(
            "monster_generate",
            "Generate Monster",
            "generator",
            (
                "Name Options",
                "Classification",
                "Appearance",
                "Biology or Nature",
                "Habitat",
                "Behavior",
                "Needs",
                "Abilities",
                "Weaknesses",
                "Signs and Traces",
                "Ecology",
                "Cultural Significance",
                "Encounter Concepts",
                "Escalation",
                "Narrative Role",
            ),
            ("creature", "character"),
        ),
        task(
            "npc_generate",
            "Generate NPC",
            "generator",
            (
                "Name Options",
                "Role",
                "Motivation",
                "Appearance",
                "Personality",
                "Voice",
                "Resources",
                "Relationships",
                "Secrets",
                "Conflict Potential",
                "Entry Points",
                "Long-term Arc",
            ),
            ("character",),
        ),
        task(
            "continuity_review",
            "Continuity Review",
            "continuity",
            (
                "Source-supported Concerns",
                "Possible Concerns",
                "Questions for Author",
                "Suggestions",
            ),
            ("plot_thread", "clue", "reveal", "knowledge"),
        ),
        task(
            "thread_payoff",
            "Thread Payoff Opportunities",
            "continuity",
            ("Open Threads", "Promises", "Payoff Options", "Timing Risks", "Questions"),
            ("plot_thread", "reveal"),
        ),
        task(
            "timeline_review",
            "Timeline Contradiction Review",
            "timeline",
            (
                "Chronology",
                "Reader Order",
                "Possible Ordering Issues",
                "Missing Transitions",
                "Questions",
            ),
            ("timeline_event", "event_relation"),
        ),
        task(
            "timeline_summary",
            "Chronology Summary",
            "timeline",
            (
                "Established Events",
                "Uncertain Events",
                "Causal Chain",
                "Reader Exposure",
                "Open Questions",
            ),
            ("timeline_event",),
        ),
        task(
            "deck_interpret",
            "Interpret Draw in World Context",
            "deck",
            (
                "Card and Position Reading",
                "World-specific Interpretation",
                "Three Story Directions",
                "Continuity Fit",
                "Questions",
            ),
            ("draw_interpretation", "plot_thread"),
        ),
        task(
            "voice_analyze",
            "Analyze Voice Sample",
            "voice",
            (
                "Prose Guidance",
                "Dialogue Guidance",
                "Sentence Rhythm",
                "Paragraph Rhythm",
                "Diction",
                "Imagery",
                "Humor",
                "Emotional Distance",
                "Exposition",
                "Prohibited Tendencies",
                "Intentional Quirks",
            ),
            ("voice_profile",),
        ),
        task(
            "editorial_developmental",
            "Developmental Review",
            "editorial",
            ("Source Excerpt", "Concern", "Importance", "Explanation", "Suggestion"),
        ),
        task(
            "editorial_tighten",
            "Tighten Passage",
            "editorial",
            ("Original", "Proposed Text", "Changes and Voice Preservation"),
            ("scene_revision",),
        ),
        task(
            "editorial_tension",
            "Increase Tension",
            "editorial",
            ("Original", "Proposed Text", "Tension Changes", "Voice Preservation"),
            ("scene_revision",),
        ),
    )
}

CATEGORIES = tuple(dict.fromkeys(item.category for item in TASKS.values()))


def get_task(key):
    return TASKS[key]
