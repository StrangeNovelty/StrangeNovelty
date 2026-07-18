from pathlib import Path

from django.template import engines
from django.urls import reverse


def test_integrated_navigation_exposes_complete_bounded_product_shell():
    source = Path("templates/includes/primary_navigation.html").read_text()
    for label in (
        "Dashboard",
        "Story Workshop",
        "Scenes",
        "Characters",
        "Plot Threads",
        "Timeline",
        "World",
        "Decks",
        "AI Studio",
        "Research &amp; Artwork",
        "Publication",
        "Search",
        "Create",
        "Manual",
        "Brainstorm",
        "Family &amp; Groups",
    ):
        assert f">{label}<" in source
    assert 'aria-current="page"' in source


def test_integrated_module_shells_use_shared_navigation_and_context_help():
    for name in (
        "ai_assistance/base.html",
        "continuity/base.html",
        "decks/base.html",
        "library/base.html",
        "publishing/base.html",
        "timeline/base.html",
    ):
        source = Path("templates", name).read_text()
        assert "includes/primary_navigation.html" in source
    assert "Continuity tracks promises" in Path("templates/continuity/base.html").read_text()
    assert "Timeline records when events occur" in Path("templates/timeline/base.html").read_text()


def test_new_integration_routes_and_all_templates_compile():
    assert reverse("quick-create") == "/create/"
    assert reverse("product-guide") == "/help/"
    engine = engines["django"]
    for path in Path("templates").rglob("*.html"):
        engine.get_template(str(path.relative_to("templates")))


def test_manual_onboarding_and_visual_shell_contracts_are_present():
    manual = Path("templates/workspaces/product_guide.html").read_text()
    for anchor in (
        "getting-started",
        "writing",
        "characters",
        "worldbuilding",
        "continuity",
        "timeline",
        "decks",
        "ai",
        "library",
        "publishing",
        "where-does-this-go",
        "workflows",
    ):
        assert f'id="{anchor}"' in manual
    for phrase in (
        "Start a new web serial",
        "Plan a Chapter",
        "Write a Scene",
        "Track a Secret",
        "Compile a manuscript",
    ):
        assert phrase in manual

    dashboard = Path("templates/workspaces/home.html").read_text()
    assert 'aria-label="Creative context"' in dashboard
    assert 'role="progressbar"' in dashboard
    assert "guided-steps" in dashboard
    assert "Open Manual" in dashboard

    scene = Path("templates/scenes/editor.html").read_text()
    assert "context-drawer" in scene
    assert "Scene Brief &amp; AI" in scene
    assert "scene-editor-panel" in scene

    css = Path("static/strange_novelty/app.css").read_text()
    assert "--color-surface-nested" in css
    assert ".manual-layout" in css
    assert "@media (max-width: 52rem)" in css
