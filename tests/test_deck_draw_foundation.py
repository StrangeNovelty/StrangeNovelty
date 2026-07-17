from pathlib import Path

from django.urls import reverse

from decks.models import DrawCardHistory, DrawConversion, DrawDeckSelection, SavedDraw


def test_draw_domain_is_explicit_and_future_safe():
    assert SavedDraw._meta.pk.get_internal_type() == "UUIDField"
    assert DrawDeckSelection._meta.get_field("deck").related_model.__name__ == "Deck"
    assert DrawCardHistory._meta.get_field("previous_card").related_model.__name__ == "DeckCard"
    target_fields = {field.name for field in DrawConversion._meta.fields}
    assert {
        "character",
        "group",
        "location",
        "region",
        "codex",
        "item",
        "creature",
        "chapter",
        "work",
    } <= target_fields
    assert "plot_thread" not in target_fields


def test_draw_routes_templates_and_mutations_are_explicit():
    draw_id = "00000000-0000-0000-0000-000000000001"
    assert reverse("deck-draw-list") == "/decks/draws/"
    assert reverse("deck-draw-detail", args=(draw_id,)).startswith("/decks/draws/")
    root = Path(__file__).parents[1]
    detail = (root / "templates/decks/draw_detail.html").read_text()
    interpretation = (root / "templates/decks/draw_interpretation.html").read_text()
    assert "creative table" in detail and "csrf_token" in detail
    assert "World-aware guidance" in detail
    assert "Original Card" not in interpretation
    assert "source_file" not in detail and "DECK_AUDIT_ROOT" not in detail


def test_draw_styles_are_responsive_and_wrap_long_content():
    css = (Path(__file__).parents[1] / "static/strange_novelty/app.css").read_text()
    assert ".draw-table" in css and "overflow-wrap: anywhere" in css
    assert "max-width: 720px" in css
