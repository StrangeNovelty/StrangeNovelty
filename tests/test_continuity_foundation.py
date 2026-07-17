from pathlib import Path

from django.urls import reverse

from continuity.models import (
    CharacterKnowledgeRecord,
    PlotThread,
    ReaderKnowledgeRecord,
    Secret,
    ThreadClue,
    ThreadReveal,
)


def test_continuity_domain_is_explicit():
    assert PlotThread._meta.pk.get_internal_type() == "UUIDField"
    assert Secret._meta.get_field("truth_statement")
    assert ThreadClue._meta.get_field("thread").related_model is PlotThread
    assert ThreadReveal._meta.get_field("thread").related_model is PlotThread
    assert ReaderKnowledgeRecord._meta.get_field("secret").related_model is Secret
    assert (
        CharacterKnowledgeRecord._meta.get_field("character").related_model.__name__ == "Character"
    )


def test_continuity_routes_templates_and_docs_are_present():
    identifier = "00000000-0000-0000-0000-000000000001"
    assert reverse("continuity-home") == "/continuity/"
    assert reverse("continuity-thread-detail", args=(identifier,)).startswith(
        "/continuity/threads/"
    )
    root = Path(__file__).parents[1]
    detail = (root / "templates/continuity/thread_detail.html").read_text()
    docs = (root / "docs/reference/continuity-domain.md").read_text()
    assert "Clues and Reveals" in detail and "csrf_token" in detail
    assert "Objective story truth" in docs and "Reader Knowledge" in docs


def test_existing_product_surfaces_include_compact_continuity_links():
    root = Path(__file__).parents[1] / "templates"
    for path in (
        "stories/chapter_detail.html",
        "scenes/editor.html",
        "stories/work_detail.html",
        "characters/detail.html",
        "decks/draw_detail.html",
    ):
        assert "Continuity" in (root / path).read_text()
