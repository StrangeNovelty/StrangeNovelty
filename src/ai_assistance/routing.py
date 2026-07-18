from dataclasses import dataclass

from django.conf import settings

WRITING = "writing"
OUTLINING = "outlining"
BRAINSTORMING = "brainstorming"
ANALYSIS = "analysis"
FALLBACK = "fallback"


TASK_ROUTES = {
    # Writing and voice-preserving transformations.
    "scene_rewrite": WRITING,
    "editorial_tighten": WRITING,
    "editorial_tension": WRITING,
    "manuscript_back_cover": WRITING,
    "submission_summary": WRITING,
    # Planning, structure, and chronology synthesis.
    "chapter_directions": OUTLINING,
    "chapter_outline": OUTLINING,
    "scene_brief": OUTLINING,
    "timeline_summary": OUTLINING,
    "chapter_reference_brief": OUTLINING,
    "manuscript_summary": OUTLINING,
    "manuscript_synopsis": OUTLINING,
    # Divergent development and alternatives.
    "story_chat": BRAINSTORMING,
    "brainstorm_plot": BRAINSTORMING,
    "brainstorm_realm": BRAINSTORMING,
    "brainstorm_npc": BRAINSTORMING,
    "brainstorm_monster": BRAINSTORMING,
    "brainstorm_item": BRAINSTORMING,
    "research_story": BRAINSTORMING,
    "visual_direction": BRAINSTORMING,
    "character_deepen": BRAINSTORMING,
    "ability_next": BRAINSTORMING,
    "location_develop": BRAINSTORMING,
    "region_develop": BRAINSTORMING,
    "group_develop": BRAINSTORMING,
    "codex_develop": BRAINSTORMING,
    "item_generate": BRAINSTORMING,
    "monster_generate": BRAINSTORMING,
    "npc_generate": BRAINSTORMING,
    "thread_payoff": BRAINSTORMING,
    "deck_interpret": BRAINSTORMING,
    # Source-grounded review and diagnosis.
    "research_summary": ANALYSIS,
    "research_compare": ANALYSIS,
    "publication_readiness": ANALYSIS,
    "compilation_consistency": ANALYSIS,
    "chapter_continuity": ANALYSIS,
    "chapter_pacing": ANALYSIS,
    "chapter_voice": ANALYSIS,
    "scene_revision": ANALYSIS,
    "character_knowledge": ANALYSIS,
    "ability_consistency": ANALYSIS,
    "continuity_review": ANALYSIS,
    "timeline_review": ANALYSIS,
    "voice_analyze": ANALYSIS,
    "editorial_developmental": ANALYSIS,
}


@dataclass(frozen=True, slots=True)
class ModelRoute:
    category: str
    primary: str
    alternates: tuple[str, ...] = ()


def route_for_task(task_key: str, *, model_override: str = "") -> ModelRoute:
    category = TASK_ROUTES.get(task_key, FALLBACK)
    override = model_override.strip()
    if override:
        return ModelRoute(category=category, primary=override)
    setting_name = {
        WRITING: "AI_MODEL_WRITING",
        OUTLINING: "AI_MODEL_OUTLINING",
        BRAINSTORMING: "AI_MODEL_BRAINSTORMING",
        ANALYSIS: "AI_MODEL_ANALYSIS",
    }.get(category)
    primary = getattr(settings, setting_name, "").strip() if setting_name else ""
    primary = primary or settings.AI_MODEL
    alternates = ()
    if category == WRITING:
        alternate = settings.AI_MODEL_WRITING_ALTERNATE.strip()
        if alternate and alternate != primary:
            alternates = (alternate,)
    return ModelRoute(category=category, primary=primary, alternates=alternates)


def scene_suggestion_route() -> ModelRoute:
    return route_for_task("scene_rewrite")
