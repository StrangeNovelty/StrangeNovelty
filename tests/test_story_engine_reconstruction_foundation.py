from pathlib import Path

from django.template import engines
from django.urls import reverse

from ai_assistance.brainstorm import MODES
from ai_assistance.routing import BRAINSTORMING, TASK_ROUTES
from ai_assistance.tasks import TASKS


def test_brainstorm_modes_restore_desktop_generator_contracts():
    assert tuple(MODES) == ("plot", "realm", "npc", "monster", "item")
    for mode in MODES.values():
        assert mode.task_key in TASKS
        assert TASK_ROUTES[mode.task_key] == BRAINSTORMING
        assert TASKS[mode.task_key].output_sections
        assert mode.constraints
    assert TASKS["brainstorm_realm"].conversion_targets == ("location", "region")
    assert TASKS["brainstorm_monster"].conversion_targets == ("creature", "character")


def test_brainstorm_routes_templates_and_universal_apply_contract():
    assert reverse("brainstorm-list") == "/brainstorm/"
    assert reverse("brainstorm-create") == "/brainstorm/new/"
    list_template = Path("templates/ai_assistance/brainstorm_list.html").read_text()
    detail = Path("templates/ai_assistance/brainstorm_detail.html").read_text()
    review = Path("templates/ai_assistance/creative_review.html").read_text()
    chat = Path("templates/ai_assistance/chat.html").read_text()
    assert "Cards, story context, constraints" in list_template
    assert "Review &amp; Apply to Story" in detail
    assert "Universal reviewed application" in review
    assert "Confirm Apply to Story" in review
    assert "Review &amp; Apply to Story" in chat
    assert "provider output" in detail and "author_notes" in detail
    engines["django"].get_template("ai_assistance/brainstorm_list.html")
    engines["django"].get_template("ai_assistance/brainstorm_detail.html")


def test_binding_desktop_navigation_and_dashboard_orientation_are_visible():
    nav = Path("templates/includes/primary_navigation.html").read_text()
    for heading in ("Overview", "World", "Characters", "Story", "Craft", "Tools"):
        assert f">{heading}<" in nav
    for destination in (
        "Dashboard",
        "Brainstorm",
        "Plot Threads",
        "Story Workshop",
        "Family &amp; Groups",
        "AI Studio",
        "Research &amp; Artwork",
        "Publication",
        "Manual",
    ):
        assert f">{destination}<" in nav
    dashboard = Path("templates/workspaces/home.html").read_text()
    assert "Continue session" in dashboard
    assert "Persistent conversation" in dashboard
    assert "Story Chat" in dashboard


def test_brainstorm_css_is_responsive_and_keeps_result_beside_context():
    css = Path("static/strange_novelty/app.css").read_text()
    assert ".brainstorm-form" in css
    assert "grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr)" in css
    assert ".brainstorm-result-panel { position: sticky" in css
    assert "@media (max-width: 45rem)" in css
