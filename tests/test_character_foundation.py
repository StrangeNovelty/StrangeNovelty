import uuid
from pathlib import Path

from django.urls import resolve, reverse

from characters.forms import CharacterCreateForm, CharacterForm
from characters.models import Character, CharacterScene


def test_character_schema_is_typed_workspace_owned_and_timestamped() -> None:
    fields = {field.name for field in Character._meta.fields}
    assert fields == {
        "id",
        "workspace",
        "name",
        "aliases",
        "role",
        "status",
        "summary",
        "appearance",
        "personality",
        "goals",
        "internal_conflict",
        "external_conflict",
        "voice_notes",
        "notes",
        "created_at",
        "updated_at",
    }
    assert Character._meta.pk.__class__.__name__ == "UUIDField"
    assert Character._meta.get_field("workspace").remote_field.on_delete.__name__ == "PROTECT"
    assert {field.name for field in CharacterScene._meta.fields} == {
        "id",
        "workspace",
        "character",
        "scene",
        "created_at",
    }


def test_character_forms_keep_creation_small_and_dossier_explicit() -> None:
    assert tuple(CharacterCreateForm().fields) == (
        "name",
        "aliases",
        "role",
        "status",
        "summary",
    )
    assert tuple(CharacterForm().fields) == (
        "name",
        "aliases",
        "role",
        "status",
        "summary",
        "appearance",
        "personality",
        "goals",
        "internal_conflict",
        "external_conflict",
        "voice_notes",
        "notes",
    )


def test_character_routes_resolve() -> None:
    character_id = uuid.uuid4()
    scene_id = uuid.uuid4()
    assert resolve(reverse("character-list")).url_name == "character-list"
    assert resolve(reverse("character-create")).url_name == "character-create"
    assert (
        resolve(reverse("character-detail", kwargs={"character_id": character_id})).url_name
        == "character-detail"
    )
    assert (
        resolve(reverse("character-scene-link", kwargs={"character_id": character_id})).url_name
        == "character-scene-link"
    )
    assert (
        resolve(
            reverse(
                "character-scene-unlink",
                kwargs={"character_id": character_id, "scene_id": scene_id},
            )
        ).url_name
        == "character-scene-unlink"
    )
    assert (
        resolve(reverse("scene-characters-update", kwargs={"scene_id": scene_id})).url_name
        == "scene-characters-update"
    )


def test_character_templates_are_dossier_oriented_and_provider_free() -> None:
    root = Path(__file__).parents[1]
    templates = root / "templates/characters"
    detail = (templates / "detail.html").read_text(encoding="utf-8")
    list_template = (templates / "list.html").read_text(encoding="utf-8")
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(templates.glob("*.html"))
    )
    for heading in (
        "Identity",
        "Presence",
        "Desire and pressure",
        "On the page",
        "Scene appearances",
    ):
        assert heading in detail
    assert "Create Character" in list_template
    assert "No Characters yet" in list_template
    assert "https://" not in combined
    assert "provider" not in combined.casefold()
    assert "localStorage" not in combined


def test_application_navigation_exposes_characters() -> None:
    root = Path(__file__).parents[1] / "templates"
    shell_templates = [
        root / "workspaces/home.html",
        root / "scenes/list.html",
        root / "scenes/create.html",
        root / "scenes/editor.html",
        root / "scenes/search.html",
        root / "ai_assistance/request.html",
        root / "ai_assistance/request_status.html",
        root / "ai_assistance/review.html",
    ]
    shared_navigation = (root / "includes/primary_navigation.html").read_text(encoding="utf-8")
    assert "{% url 'character-list' %}" in shared_navigation
    for template_path in shell_templates:
        source = template_path.read_text(encoding="utf-8")
        assert "{% url 'character-list' %}" in source or "primary_navigation.html" in source


def test_character_migration_is_narrow_and_typed() -> None:
    migration = (Path(__file__).parents[1] / "src/characters/migrations/0001_initial.py").read_text(
        encoding="utf-8"
    )
    assert "CreateModel" in migration
    assert "CharacterScene" in migration
    assert "UUIDField" in migration
    assert "PROTECT" in migration
    assert "RunPython" not in migration
    assert "RunSQL" not in migration
    for forbidden in ("GenericForeignKey", "ContentType", "JSONField", "embedding"):
        assert forbidden not in migration
