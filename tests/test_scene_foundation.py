import unicodedata
import uuid
from importlib import import_module

import pytest
from django.db import models
from django.db.migrations.operations.models import CreateModel
from django.db.migrations.operations.special import RunPython

from accounts.models import Account
from scenes.content import (
    CONTENT_FORMAT_VERSION,
    MAX_CONTENT_CHARACTERS,
    NORMALIZATION_VERSION,
    content_sha256,
    normalize_scene_content,
)
from scenes.exceptions import (
    ImmutableMutationOperationError,
    ImmutableRevisionError,
    InvalidSceneContent,
    InvalidSceneOrdering,
    InvalidSceneTitle,
)
from scenes.models import MutationOperation, Scene, SceneRevision
from scenes.services import validate_scene_ordering, validate_scene_title
from workspaces.models import Workspace


def test_scene_domain_models_use_uuid_primary_keys() -> None:
    workspace = Workspace(name="Synthetic Workspace")
    scene = Scene(workspace=workspace, title="Synthetic Scene", ordering=1000)
    operation = MutationOperation(workspace=workspace, scene=scene)
    revision = SceneRevision(
        workspace=workspace,
        scene=scene,
        content="",
        content_sha256=content_sha256(""),
        revision_number=1,
        mutation_operation=operation,
    )

    assert isinstance(scene.pk, uuid.UUID)
    assert isinstance(operation.pk, uuid.UUID)
    assert isinstance(revision.pk, uuid.UUID)
    assert Scene._meta.pk.get_internal_type() == "UUIDField"
    assert MutationOperation._meta.pk.get_internal_type() == "UUIDField"
    assert SceneRevision._meta.pk.get_internal_type() == "UUIDField"


def test_scene_schema_has_no_authoritative_body_field() -> None:
    field_names = {field.name for field in Scene._meta.fields}

    assert field_names == {
        "id",
        "workspace",
        "title",
        "lifecycle",
        "ordering",
        "version",
        "current_revision",
        "work",
        "volume",
        "arc",
        "chapter",
        "structure_order",
        "created_at",
        "updated_at",
    }
    assert Scene._meta.get_field("workspace").remote_field.on_delete is models.PROTECT
    assert Scene._meta.get_field("current_revision").remote_field.on_delete is models.PROTECT


def test_lifecycle_ordering_version_constraints_and_index_are_explicit() -> None:
    assert set(Scene.Lifecycle.values) == {"active", "archived", "trashed"}
    constraint_names = {constraint.name for constraint in Scene._meta.constraints}
    index_names = {index.name for index in Scene._meta.indexes}

    assert constraint_names == {
        "scene_title_contains_nonspace",
        "scene_lifecycle_valid",
        "scene_ordering_nonnegative",
        "scene_version_nonnegative",
        "scene_structure_requires_work",
        "scene_placement_order_consistent",
        "unique_scene_ordering_in_workspace",
    }
    assert index_names == {"scene_ws_lifecycle_order_idx", "scene_ws_structure_idx"}


def test_scene_title_and_ordering_validation() -> None:
    assert validate_scene_title("  Synthetic Scene  ") == "Synthetic Scene"
    assert validate_scene_ordering(1000) == 1000

    for invalid in ("", "   ", "bad\x00title", "x" * 201):
        with pytest.raises(InvalidSceneTitle):
            validate_scene_title(invalid)
    for invalid_order in (-1, True, 1.5):
        with pytest.raises(InvalidSceneOrdering):
            validate_scene_ordering(invalid_order)  # type: ignore[arg-type]


def test_normalization_is_lf_nfc_deterministic_and_whitespace_preserving() -> None:
    decomposed = "Cafe\u0301"
    value = f"  {decomposed}\r\n\rSecond line  \n"

    normalized = normalize_scene_content(value)

    assert normalized == "  Café\n\nSecond line  \n"
    assert unicodedata.is_normalized("NFC", normalized)
    assert normalize_scene_content(normalized) == normalized
    assert CONTENT_FORMAT_VERSION == "plain-text-v1"
    assert NORMALIZATION_VERSION == "plain-text-nfc-lf-v1"
    assert content_sha256(normalized) == content_sha256(normalized)


def test_normalization_allows_empty_unicode_and_rejects_invalid_content() -> None:
    assert normalize_scene_content("") == ""
    assert normalize_scene_content("文字🙂") == "文字🙂"
    with pytest.raises(InvalidSceneContent, match="NUL"):
        normalize_scene_content("before\x00after")
    with pytest.raises(InvalidSceneContent, match="must be text"):
        normalize_scene_content(b"binary")  # type: ignore[arg-type]
    with pytest.raises(InvalidSceneContent, match="character limit"):
        normalize_scene_content("x" * (MAX_CONTENT_CHARACTERS + 1))


def test_revision_and_operation_fields_are_bounded_and_content_free() -> None:
    revision_fields = {field.name for field in SceneRevision._meta.fields}
    operation_fields = {field.name for field in MutationOperation._meta.fields}

    assert "content" in revision_fields
    assert revision_fields == {
        "id",
        "workspace",
        "scene",
        "content",
        "content_sha256",
        "revision_number",
        "content_format_version",
        "normalization_version",
        "base_revision",
        "restored_from",
        "source",
        "actor",
        "mutation_operation",
        "created_at",
    }
    assert operation_fields == {
        "id",
        "workspace",
        "operation_type",
        "source",
        "actor",
        "scene",
        "created_at",
    }
    assert set(MutationOperation.OperationType.values) == {
        "scene_created",
        "scene_content_revised",
        "scene_imported",
        "scene_revision_imported",
    }
    assert list(MutationOperation.Source.values) == ["owner", "import"]
    assert list(SceneRevision.Source.values) == ["owner", "import"]


def test_revision_and_operation_instance_updates_are_rejected_before_database_use() -> None:
    workspace = Workspace(name="Synthetic Workspace")
    scene = Scene(workspace=workspace, title="Synthetic Scene", ordering=1000)
    operation = MutationOperation(workspace=workspace, scene=scene)
    revision = SceneRevision(
        workspace=workspace,
        scene=scene,
        content="",
        content_sha256=content_sha256(""),
        revision_number=1,
        mutation_operation=operation,
    )
    operation._state.adding = False
    revision._state.adding = False

    with pytest.raises(ImmutableMutationOperationError):
        operation.save()
    with pytest.raises(ImmutableMutationOperationError):
        operation.delete()
    with pytest.raises(ImmutableRevisionError):
        revision.save()
    with pytest.raises(ImmutableRevisionError):
        revision.delete()


def test_phase3_migration_contains_only_expected_schema_models() -> None:
    migration_module = import_module("scenes.migrations.0001_initial")
    migration = migration_module.Migration("0001_initial", "scenes")
    created_models = {
        operation.name for operation in migration.operations if isinstance(operation, CreateModel)
    }

    assert migration.initial is True
    assert created_models == {"Scene", "MutationOperation", "SceneRevision"}
    assert not any(isinstance(operation, RunPython) for operation in migration.operations)


def test_no_parallel_integer_identities_exist() -> None:
    for model in (Scene, SceneRevision, MutationOperation):
        integer_identity_fields = [
            field
            for field in model._meta.fields
            if field.primary_key and field.get_internal_type() != "UUIDField"
        ]
        assert integer_identity_fields == []


def test_actor_references_are_protective() -> None:
    assert SceneRevision._meta.get_field("actor").remote_field.on_delete is models.PROTECT
    assert MutationOperation._meta.get_field("actor").remote_field.on_delete is models.PROTECT
    assert Account._meta.pk.get_internal_type() == "UUIDField"
