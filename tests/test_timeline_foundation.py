from pathlib import Path

from django.urls import reverse

from timeline.models import Timeline, TimelineEvent, TimelineEventRelation


def test_timeline_domain_uses_explicit_chronology_and_relations():
    assert Timeline._meta.pk.get_internal_type() == "UUIDField"
    assert TimelineEvent._meta.get_field("start_sort_value").get_internal_type() == "DecimalField"
    assert TimelineEvent._meta.get_field("end_sort_value").null
    assert TimelineEventRelation._meta.get_field("source").related_model is TimelineEvent
    assert not any(field.name == "generic_target" for field in TimelineEvent._meta.fields)


def test_timeline_routes_templates_and_documentation_exist():
    identifier = "00000000-0000-0000-0000-000000000001"
    assert reverse("timeline-home") == "/timelines/"
    assert reverse("timeline-event-detail", args=(identifier,)).startswith("/timeline-events/")
    root = Path(__file__).parents[1]
    dossier = (root / "templates/timeline/event_detail.html").read_text()
    cross_reference = (root / "templates/timeline/cross_reference.html").read_text()
    docs = (root / "docs/reference/timeline-domain.md").read_text()
    assert "Chronology" in dossier and "csrf_token" in dossier
    assert "All selected Characters together" in cross_reference
    assert "Chronology remains distinct from reader order" in docs


def test_existing_surfaces_expose_timeline_navigation_without_graph_controls():
    root = Path(__file__).parents[1]
    for path in (
        "templates/stories/chapter_detail.html",
        "templates/scenes/editor.html",
        "templates/characters/detail.html",
        "templates/continuity/thread_detail.html",
        "templates/decks/draw_interpretation.html",
    ):
        content = (root / path).read_text()
        assert "Timeline" in content
        assert "graph database" not in content.lower()
