import uuid
from pathlib import Path

from django.db.models.deletion import PROTECT
from django.urls import resolve, reverse

from scenes.models import Scene
from stories.forms import ChapterForm, ScenePlacementForm, WorkForm
from stories.models import Arc, Chapter, Volume, Work


def test_story_structure_models_are_typed_workspace_owned_and_protective() -> None:
    assert {field.name for field in Work._meta.fields} == {
        "id",
        "workspace",
        "title",
        "subtitle",
        "work_type",
        "status",
        "premise",
        "description",
        "intended_audience",
        "genre_notes",
        "created_at",
        "updated_at",
    }
    assert Work._meta.get_field("workspace").remote_field.on_delete is PROTECT
    for model, parent in ((Volume, "work"), (Arc, "work"), (Chapter, "work")):
        assert model._meta.get_field(parent).remote_field.on_delete is PROTECT
        assert model._meta.pk.__class__.__name__ == "UUIDField"
    assert Chapter._meta.get_field("pov_character").remote_field.on_delete is PROTECT


def test_scene_placement_is_additive_nullable_and_protective() -> None:
    for field_name in ("work", "volume", "arc", "chapter"):
        field = Scene._meta.get_field(field_name)
        assert field.null is True
        assert field.blank is True
        assert field.remote_field.on_delete is PROTECT
    assert Scene._meta.get_field("structure_order").null is True
    constraint_names = {constraint.name for constraint in Scene._meta.constraints}
    assert "scene_placement_order_consistent" in constraint_names
    assert "scene_structure_requires_work" in constraint_names


def test_story_structure_choices_and_forms_are_bounded() -> None:
    assert {value for value, _ in Work.WorkType.choices} == {
        "web_serial",
        "novel",
        "novella",
        "short_story",
        "screenplay",
        "stage_play",
        "comic",
        "other",
    }
    assert {value for value, _ in Work.Status.choices} == {
        "idea",
        "planning",
        "drafting",
        "revising",
        "complete",
        "hiatus",
        "archived",
    }
    assert tuple(WorkForm().fields) == (
        "title",
        "subtitle",
        "work_type",
        "status",
        "premise",
        "description",
        "intended_audience",
        "genre_notes",
    )
    assert "pov_character" in ChapterForm.base_fields
    assert tuple(ScenePlacementForm.base_fields) == (
        "work",
        "volume",
        "arc",
        "chapter",
        "structure_order",
    )


def test_story_structure_routes_are_named() -> None:
    work_id = uuid.uuid4()
    volume_id = uuid.uuid4()
    arc_id = uuid.uuid4()
    chapter_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    routes = {
        "work-list": {},
        "work-create": {},
        "work-detail": {"work_id": work_id},
        "work-delete": {"work_id": work_id},
        "volume-create": {"work_id": work_id},
        "volume-edit": {"work_id": work_id, "volume_id": volume_id},
        "volume-delete": {"work_id": work_id, "record_id": volume_id},
        "arc-create": {"work_id": work_id},
        "arc-edit": {"work_id": work_id, "arc_id": arc_id},
        "arc-delete": {"work_id": work_id, "record_id": arc_id},
        "chapter-create": {"work_id": work_id},
        "chapter-detail": {"work_id": work_id, "chapter_id": chapter_id},
        "chapter-delete": {"work_id": work_id, "record_id": chapter_id},
        "chapter-scene-create": {"work_id": work_id, "chapter_id": chapter_id},
        "chapter-scene-attach": {"work_id": work_id, "chapter_id": chapter_id},
        "scene-placement-update": {"scene_id": scene_id},
    }
    for name, kwargs in routes.items():
        assert resolve(reverse(name, kwargs=kwargs)).url_name == name


def test_templates_expose_works_named_routes_and_post_only_structure_mutations() -> None:
    root = Path(__file__).parents[1] / "templates"
    for template in root.rglob("*.html"):
        content = template.read_text()
        if '<nav class="primary-nav">' in content:
            assert "{% url 'work-list' %}" in content
    editor = (root / "scenes/editor.html").read_text()
    chapter = (root / "stories/chapter_detail.html").read_text()
    delete = (root / "stories/structure_delete.html").read_text()
    assert "Story Placement" in editor
    assert "scene-placement-update" in editor
    for content in (editor, chapter, delete):
        assert 'method="post"' in content
        assert "{% csrf_token %}" in content
    assert "work-detail" in chapter
    assert "scene-editor" in chapter


def test_story_structure_search_and_dashboard_are_integrated() -> None:
    root = Path(__file__).parents[1]
    search = (root / "templates/scenes/search.html").read_text()
    dashboard = (root / "templates/workspaces/home.html").read_text()
    for heading in ("Works", "Chapters"):
        assert f">{heading}<" in search
    assert "work-detail" in search
    assert "chapter-detail" in search
    assert "active_work_count" in dashboard
    assert "recent_work" in dashboard


def test_story_structure_migrations_are_additive_and_data_safe() -> None:
    root = Path(__file__).parents[1] / "src"
    stories_migration = (root / "stories/migrations/0001_initial.py").read_text()
    scene_migration = (
        root / "scenes/migrations/0005_scene_arc_scene_chapter_scene_structure_order_and_more.py"
    ).read_text()
    for model in ("Work", "Volume", "Arc", "Chapter"):
        assert model in stories_migration
    for field in ("work", "volume", "arc", "chapter", "structure_order"):
        assert f'name="{field}"' in scene_migration
    assert scene_migration.count("null=True") >= 5
    for forbidden in ("RunPython", "RunSQL", "GenericForeignKey", "JSONField"):
        assert forbidden not in stories_migration
        assert forbidden not in scene_migration


def test_story_structure_styles_cover_focus_overflow_and_narrow_layouts() -> None:
    css = (Path(__file__).parents[1] / "static/strange_novelty/app.css").read_text()
    assert ".work-card:focus-visible" in css
    assert ".structure-scene-row:focus-visible" in css
    assert "overflow-wrap: anywhere" in css
    narrow = css.split("@media (max-width: 48rem)", maxsplit=1)[1]
    for selector in (".work-card-list", ".structure-summary-strip", ".chapter-scene-actions"):
        assert selector in narrow
