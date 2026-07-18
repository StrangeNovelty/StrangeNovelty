from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from ai_assistance.tasks import TASKS
from stories.forms import ChapterPacingProfileForm, SceneBriefForm
from stories.models import (
    ChapterBeat,
    ChapterChecklistItem,
    ChapterPacingProfile,
    ChapterPlanningSnapshot,
    SceneBrief,
    WritingDelta,
)

ROOT = Path(__file__).resolve().parents[1]


def test_workshop_models_keep_planning_and_prose_separate():
    assert ChapterBeat._meta.get_field("intended_scene").null
    assert (
        SceneBrief._meta.get_field("source_revision").remote_field.model.__name__ == "SceneRevision"
    )
    assert ChapterPlanningSnapshot._meta.get_field("beat_data").get_internal_type() == "JSONField"
    assert WritingDelta._meta.get_field("revision").one_to_one
    assert ChapterChecklistItem._meta.get_field("completed").default is False


def test_pacing_scores_are_bounded_and_optional():
    with pytest.raises(ValidationError):
        ChapterPacingProfile(tension_score=11).clean()
    assert ChapterPacingProfileForm().fields["tension_score"].required is False
    assert ChapterPacingProfile._meta.get_field("tension_score").null


def test_scene_brief_form_never_edits_scene_prose_or_revision_identity():
    assert "source_revision" not in SceneBriefForm.Meta.fields
    assert "scene" not in SceneBriefForm.Meta.fields
    assert "content" not in SceneBriefForm.Meta.fields


def test_workshop_routes_and_ai_tasks_are_live():
    work = "00000000-0000-0000-0000-000000000001"
    chapter = "00000000-0000-0000-0000-000000000002"
    assert reverse("series-map", kwargs={"work_id": work}).endswith("/series-map/")
    assert reverse("pacing-map", kwargs={"work_id": work}).endswith("/pacing-map/")
    assert reverse("chapter-pacing", kwargs={"work_id": work, "chapter_id": chapter}).endswith(
        "/pacing/"
    )
    assert {"chapter_pacing", "chapter_voice"}.issubset(TASKS)


def test_templates_are_accessible_responsive_and_post_backed():
    chapter = (ROOT / "templates/stories/chapter_detail.html").read_text()
    pacing = (ROOT / "templates/stories/pacing_map.html").read_text()
    css = (ROOT / "static/strange_novelty/app.css").read_text()
    for label in (
        "Chapter Beats",
        "Scene Briefs",
        "Pacing Profile",
        "Planning Snapshots",
        "Checklist",
    ):
        assert label in chapter
    assert "{% csrf_token %}" in chapter
    assert "<table" in pacing and "<th" in pacing
    assert "overflow-wrap:anywhere" in css
    assert "@media(max-width:700px)" in css


def test_documentation_uses_only_generic_domain_language():
    text = (ROOT / "docs/reference/advanced-chapter-workshop.md").read_text()
    assert "immutable Scene revisions" in text
    assert "private-data" not in text
