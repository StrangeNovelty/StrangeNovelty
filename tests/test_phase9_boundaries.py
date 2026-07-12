from django.contrib import admin

from legacy_imports.models import (
    IdentityMapping,
    ImportBatch,
    ImportFinding,
    ImportProvenance,
    StagedRevision,
    StagedScene,
)
from scenes.models import MutationOperation, SceneRevision


def test_import_models_use_uuid_identity_and_no_source_path_or_arbitrary_payload() -> None:
    models = (
        ImportBatch,
        StagedScene,
        StagedRevision,
        ImportFinding,
        IdentityMapping,
        ImportProvenance,
    )
    for model in models:
        assert model._meta.pk.get_internal_type() == "UUIDField"
        fields = {field.name for field in model._meta.fields}
        assert not fields & {"path", "filename", "payload", "metadata", "credentials", "secret"}
    assert "content" not in {field.name for field in ImportBatch._meta.fields}
    assert "content" not in {field.name for field in ImportFinding._meta.fields}


def test_identity_mapping_is_source_evidence_not_target_identity() -> None:
    fields = {field.name for field in IdentityMapping._meta.fields}
    assert {
        "source_identifier",
        "target_uuid",
        "source_entity_type",
        "target_entity_type",
    } <= fields
    assert IdentityMapping._meta.pk.name == "id"


def test_import_admin_is_read_only_and_hides_staged_content() -> None:
    for model in (
        ImportBatch,
        StagedScene,
        StagedRevision,
        ImportFinding,
        IdentityMapping,
        ImportProvenance,
    ):
        model_admin = admin.site._registry[model]
        assert model_admin.has_add_permission(None) is False
        assert model_admin.has_change_permission(None) is False
        assert model_admin.has_delete_permission(None) is False
    assert "content" in admin.site._registry[StagedRevision].exclude


def test_import_provenance_extends_bounded_domain_choices_only() -> None:
    assert {"scene_imported", "scene_revision_imported"} <= set(
        MutationOperation.OperationType.values
    )
    assert set(MutationOperation.Source.values) == {"owner", "import"}
    assert set(SceneRevision.Source.values) == {"owner", "import"}
