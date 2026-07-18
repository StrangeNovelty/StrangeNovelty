from pathlib import Path

from django.urls import reverse

from ai_assistance.routing import ANALYSIS, WRITING, route_for_task
from ai_assistance.tasks import TASKS

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


def test_story_engine_workflow_surfaces_are_routable():
    assert reverse("world-bible") == "/world/bible/"
    assert reverse("character-relationship-web") == "/characters/relationships/"
    assert "personality" in reverse(
        "character-personality-trait-create",
        args=("11111111-1111-1111-1111-111111111111",),
    )


def test_story_workshop_has_binding_continuous_pipeline():
    template = read("templates/stories/chapter_detail.html")
    pipeline = template.split('<nav class="story-workshop-pipeline"', 1)[1].split("</nav>", 1)[0]
    expected = (
        "Outline",
        "Draft",
        "Editor",
        "Links",
        "Story Engine",
        "Scene Brief",
        "Sliders",
        "De-Slop",
        "Continuity",
        "Polish",
        "Package",
        "Publication",
    )
    positions = [pipeline.index(label) for label in expected]
    assert positions == sorted(positions)
    assert "immutable Revisions" in template
    assert "stale source material cannot be applied" in template


def test_world_bible_character_fidelity_and_manual_are_connected():
    navigation = read("templates/includes/primary_navigation.html")
    manual = read("templates/workspaces/product_guide.html")
    character = read("templates/characters/detail.html")
    assert "World Bible" in navigation
    assert "Relationship Web" in navigation
    assert "Personality Sliders" in character
    assert "World Bible" in manual and "Structured World" in manual
    assert "Apply to Story" in manual
    assert "De-Slop" in manual


def test_relationship_web_has_visual_and_accessible_representations():
    template = read("templates/characters/relationship_web.html")
    assert '<svg viewBox="0 0 100 100"' in template
    assert "A complete text list follows" in template
    assert "Accessible relationship list" in template


def test_six_pass_deslop_pipeline_is_reviewed_and_task_routed():
    analysis = (
        "deslop_pacing_analysis",
        "deslop_line_analysis",
        "deslop_tendency_analysis",
    )
    rewriting = (
        "deslop_pacing_rewrite",
        "deslop_line_rewrite",
        "deslop_final_rewrite",
    )
    assert all(key in TASKS for key in analysis + rewriting)
    assert all(route_for_task(key).category == ANALYSIS for key in analysis)
    assert all(route_for_task(key).category == WRITING for key in rewriting)
    assert all("scene_revision" in TASKS[key].conversion_targets for key in rewriting)
