import uuid
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.urls import resolve, reverse

from scenes.forms import SceneCreateForm, SceneSaveForm
from scenes.models import SceneSaveRequest
from scenes.save_requests import scene_save_fingerprint


def test_phase4_routes_resolve_without_public_api() -> None:
    assert resolve(reverse("scene-list")).url_name == "scene-list"
    assert resolve(reverse("scene-create")).url_name == "scene-create"
    scene_id = uuid.uuid4()
    assert resolve(reverse("scene-editor", kwargs={"scene_id": scene_id})).url_name == (
        "scene-editor"
    )
    assert resolve(reverse("scene-save", kwargs={"scene_id": scene_id})).url_name == "scene-save"


def test_create_form_contains_no_workspace_authority() -> None:
    form = SceneCreateForm()
    assert tuple(form.fields) == ("title",)


def test_save_form_is_complete_content_with_bounded_hidden_preconditions() -> None:
    form = SceneSaveForm()
    assert tuple(form.fields) == (
        "content",
        "expected_current_revision_id",
        "expected_scene_version",
        "idempotency_key",
        "save_intent",
    )
    assert form.fields["content"].strip is False
    assert form.fields["content"].required is False
    assert form.fields["idempotency_key"].max_length == 128


@pytest.mark.parametrize("key", ["short", "contains spaces invalid", "x" * 129])
def test_save_form_rejects_invalid_idempotency_keys(key: str) -> None:
    form = SceneSaveForm(
        {
            "content": "Synthetic text",
            "expected_current_revision_id": uuid.uuid4(),
            "expected_scene_version": 1,
            "idempotency_key": key,
            "save_intent": "explicit_save",
        }
    )
    assert not form.is_valid()
    assert "idempotency_key" in form.errors


def test_fingerprint_is_stable_sensitive_and_contains_no_content() -> None:
    scene_id = uuid.uuid4()
    revision_id = uuid.uuid4()
    first = scene_save_fingerprint(
        scene_id=scene_id,
        expected_current_revision_id=revision_id,
        expected_scene_version=1,
        normalized_content_hash="a" * 64,
        save_intent="explicit_save",
    )
    second = scene_save_fingerprint(
        scene_id=scene_id,
        expected_current_revision_id=revision_id,
        expected_scene_version=1,
        normalized_content_hash="a" * 64,
        save_intent="explicit_save",
    )
    changed = scene_save_fingerprint(
        scene_id=scene_id,
        expected_current_revision_id=revision_id,
        expected_scene_version=2,
        normalized_content_hash="a" * 64,
        save_intent="explicit_save",
    )
    assert first == second
    assert first != changed
    assert len(first) == 64
    assert "Synthetic" not in first


def test_scene_save_request_schema_has_no_private_payload() -> None:
    fields = {field.name for field in SceneSaveRequest._meta.fields}
    assert fields == {
        "id",
        "workspace",
        "account",
        "scene",
        "idempotency_key",
        "request_fingerprint",
        "state",
        "failure_classification",
        "result_revision",
        "result_scene_version",
        "created_at",
        "completed_at",
        "updated_at",
    }
    forbidden = {"content", "title", "request_body", "metadata", "csrf", "session", "error"}
    assert fields.isdisjoint(forbidden)
    assert SceneSaveRequest._meta.pk.__class__.__name__ == "UUIDField"


def test_scene_save_request_choices_are_bounded() -> None:
    record = SceneSaveRequest(state="invented", failure_classification="raw-error")
    with pytest.raises(ValidationError):
        record.full_clean(
            exclude=("workspace", "account", "scene"),
            validate_unique=False,
            validate_constraints=False,
        )


def test_phase4_migration_is_narrow_and_has_no_data_operation() -> None:
    migration_path = Path(__file__).parents[1] / "src/scenes/migrations/0002_scenesaverequest.py"
    migration = migration_path.read_text(encoding="utf-8")
    assert "CreateModel" in migration
    assert "SceneSaveRequest" in migration
    assert "UUIDField" in migration
    assert "PROTECT" in migration
    assert "RunPython" not in migration
    assert "RunSQL" not in migration
    for forbidden in ("Job", "Search", "Import", "AI", "SecurityEvent", "content',"):
        assert forbidden not in migration


def test_templates_are_server_rendered_accessible_and_externally_tracker_free() -> None:
    template_root = Path(__file__).parents[1] / "templates/scenes"
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(template_root.glob("*.html"))
    )
    assert "{% csrf_token %}" in combined
    assert "<label" in combined
    assert 'role="alert"' in combined
    assert 'role="status"' in combined
    assert "https://" not in combined
    assert "editor.js" in combined
    assert "localStorage" not in combined
    assert "force save" not in combined.casefold()


def test_scene_create_template_uses_application_shell_and_preserves_form_contract() -> None:
    template = (Path(__file__).parents[1] / "templates/scenes/create.html").read_text(
        encoding="utf-8"
    )
    assert 'class="app-shell"' in template
    assert 'aria-label="Primary navigation"' in template
    assert 'class="nav-link nav-link-active"' in template
    assert '<form class="scene-create-form" method="post">' in template
    assert "{% csrf_token %}" in template
    assert "{{ form.title }}" in template
    assert "{{ form.title.errors }}" in template
    assert "scenes/_form_errors.html" in template


def test_scene_editor_template_uses_application_shell_and_preserves_save_contract() -> None:
    template = (Path(__file__).parents[1] / "templates/scenes/editor.html").read_text(
        encoding="utf-8"
    )
    assert 'class="app-shell"' in template
    assert 'aria-label="Primary navigation"' in template
    assert "includes/primary_navigation.html" in template
    assert "action=\"{% url 'scene-save' scene.id %}\"" in template
    assert "{% csrf_token %}" in template
    assert "{% for hidden in form.hidden_fields %}{{ hidden }}{% endfor %}" in template
    assert "{{ form.content }}" in template
    assert "{{ form.content.errors }}" in template
    assert "scenes/_form_errors.html" in template
    assert 'role="status"' in template
    assert "Archived Scenes are read-only." in template
    assert "readonly" in template
    assert "editor.js" in template


def test_scene_shells_do_not_nest_main_landmarks() -> None:
    template_root = Path(__file__).parents[1] / "templates/scenes"
    for name in ("list.html", "create.html", "editor.html"):
        template = (template_root / name).read_text(encoding="utf-8")
        assert '<main class="workspace-main' not in template


def test_scene_list_titles_wrap_at_narrow_widths() -> None:
    stylesheet = (Path(__file__).parents[1] / "static/strange_novelty/app.css").read_text(
        encoding="utf-8"
    )
    assert ".scene-list-title {\n  overflow-wrap: anywhere;" in stylesheet


def test_progressive_key_generation_has_no_correctness_or_storage_dependency() -> None:
    script = (Path(__file__).parents[1] / "src/scenes/static/scenes/editor.js").read_text(
        encoding="utf-8"
    )
    assert "crypto.randomUUID" in script
    assert "localStorage" not in script
    assert "fetch(" not in script
