from pathlib import Path

from django.urls import reverse

from stories.forms import ChapterForm, ChapterSceneOrderForm
from stories.models import Chapter
from stories.search import CHAPTER_SEARCH_FIELDS
from stories.writing import READING_WORDS_PER_MINUTE

ROOT = Path(__file__).resolve().parents[1]


def test_chapter_planning_fields_are_optional_text() -> None:
    expected = {
        "concept",
        "goal",
        "key_beats",
        "emotional_arc",
        "character_focus",
        "brain_dump",
        "outline",
    }
    assert expected.issubset(field.name for field in Chapter._meta.fields)
    assert expected.issubset(ChapterForm.Meta.fields)
    for name in expected:
        assert Chapter._meta.get_field(name).blank is True


def test_chapter_search_covers_every_planning_field() -> None:
    assert {
        "goal",
        "concept",
        "key_beats",
        "emotional_arc",
        "character_focus",
        "brain_dump",
        "outline",
        "notes",
    }.issubset(CHAPTER_SEARCH_FIELDS)


def test_reading_rate_and_scene_order_form_are_bounded() -> None:
    assert READING_WORDS_PER_MINUTE == 250
    assert ChapterSceneOrderForm({"structure_order": "0"}).is_valid()
    assert not ChapterSceneOrderForm({"structure_order": "-1"}).is_valid()


def test_scene_order_and_detach_routes_are_named() -> None:
    chapter = "00000000-0000-0000-0000-000000000001"
    work = "00000000-0000-0000-0000-000000000002"
    scene = "00000000-0000-0000-0000-000000000003"
    assert reverse(
        "chapter-scene-order",
        kwargs={"work_id": work, "chapter_id": chapter, "scene_id": scene},
    ).endswith("/order/")
    assert reverse(
        "chapter-scene-detach",
        kwargs={"work_id": work, "chapter_id": chapter, "scene_id": scene},
    ).endswith("/detach/")


def test_chapter_workspace_has_sections_post_forms_and_no_dead_ai_controls() -> None:
    template = (ROOT / "templates/stories/chapter_detail.html").read_text()
    for label in ("Overview", "Intake Brief", "Outline", "Scenes", "Notes", "Brain dump"):
        assert label in template
    assert "chapter-scene-order" in template
    assert "chapter-scene-detach" in template
    assert "{% csrf_token %}" in template
    assert "Build Outline" not in template


def test_chapter_workspace_styles_cover_overflow_focus_and_narrow_layout() -> None:
    css = (ROOT / "static/strange_novelty/app.css").read_text()
    assert ".chapter-writing-workspace" in css
    assert "overflow-wrap: anywhere" in css
    assert ".chapter-writing-scene a:focus-visible" in css
    narrow = css.split("@media (max-width: 48rem)", maxsplit=1)[1]
    assert ".chapter-progress-strip" in narrow
    assert ".chapter-writing-scene" in narrow
