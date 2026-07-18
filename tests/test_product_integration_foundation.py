from pathlib import Path

from django.template import engines
from django.urls import reverse


def test_integrated_navigation_exposes_complete_bounded_product_shell():
    source = Path("templates/includes/primary_navigation.html").read_text()
    for label in (
        "Workspace",
        "Works",
        "Scenes",
        "Characters",
        "Continuity",
        "Timeline",
        "World",
        "Decks",
        "AI Studio",
        "Library",
        "Publishing",
        "Search",
        "Create",
        "Help",
    ):
        assert f">{label}<" in source
    assert ">Groups<" not in source
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
