from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrainstormMode:
    key: str
    task_key: str
    title: str
    purpose: str
    constraints: tuple[str, ...]


MODES = {
    item.key: item
    for item in (
        BrainstormMode(
            "plot",
            "brainstorm_plot",
            "Plot Seeds",
            "Develop three distinct story directions from Cards and selected story context.",
            (
                "Use only explicitly selected Characters when a cast is provided.",
                "Keep established roles and personalities intact; Cards shape circumstances, "
                "not identity.",
                "Treat Cards as lenses, metaphors, or atmosphere rather than literal requirements.",
                "Make every direction concrete enough to plan as a Chapter, Thread, or Event.",
            ),
        ),
        BrainstormMode(
            "realm",
            "brainstorm_realm",
            "Realm Builder",
            "Build a distinctive realm or territory that fits the selected world.",
            (
                "Do not duplicate a selected or established Region, Location, or Group.",
                "Ground culture, access, instability, sensory identity, and present conflict "
                "in context.",
                "Use Cards as creative lenses rather than literal requirements.",
            ),
        ),
        BrainstormMode(
            "npc",
            "brainstorm_npc",
            "NPC Generator",
            "Create a specific supporting Character with a committed story role.",
            (
                "Do not duplicate an established Character or Group member.",
                "Avoid statistically generic names, bodies, ages, presentation, and moral "
                "neutrality.",
                "Give the Character one contradiction, one immediate want, and a "
                "non-coincidental entry point.",
                "Honor the selected threat classification without softening it.",
            ),
        ),
        BrainstormMode(
            "monster",
            "brainstorm_monster",
            "Monster Generator",
            "Design a concrete Creature with ecology, threat, and story use.",
            (
                "Do not default to familiar fantasy animals or silhouettes.",
                "Specify scale, mass, texture, movement, needs, behavior, and internal logic.",
                "Make the threat explicit and include an exploitable weakness or tell.",
            ),
        ),
        BrainstormMode(
            "item",
            "brainstorm_item",
            "Item Generator",
            "Design an object with physical reality, an internal mechanism, and story "
            "consequences.",
            (
                "Avoid generic fantasy items and vague powers.",
                "Specify material, weight or handling, maker, purpose, mechanism, cost, "
                "and danger.",
                "Honor the selected discipline throughout the profile.",
            ),
        ),
    )
}


def instruction_for(session):
    mode = MODES[session.mode]
    settings = session.mode_settings or {}
    lines = [
        mode.purpose,
        "Follow these author-controlled boundaries:",
        *(f"- {rule}" for rule in mode.constraints),
    ]
    if session.focus.strip():
        lines.extend(("", "AUTHOR FOCUS:", session.focus.strip()))
    if session.exclusions.strip():
        lines.extend(("", "KEEP OUT:", session.exclusions.strip()))
    if session.mode == "npc" and settings.get("threat_level"):
        lines.extend(
            ("", f"REQUIRED THREAT CLASS: {settings['threat_level'].replace('_', ' ').title()}")
        )
    if session.mode == "item" and settings.get("discipline"):
        lines.extend(("", f"REQUIRED DISCIPLINE: {settings['discipline'].title()}"))
    lines.extend(
        (
            "",
            "Return every requested section as a Markdown level-two heading. "
            "Do not present generated material as established canon.",
        )
    )
    return "\n".join(lines)
