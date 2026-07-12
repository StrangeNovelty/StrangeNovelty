import json
import os
import uuid
from pathlib import Path

import pytest
from django.http import Http404

from accounts.models import Account
from jobs.models import IdempotencyRecord, Job
from legacy_imports.models import IdentityMapping, ImportBatch, ImportProvenance, StagedRevision
from legacy_imports.parser import FORMAT_NAME, LegacyImportError
from legacy_imports.services import (
    apply_import,
    approve_import,
    quarantine_unfinished_imports,
    stage_legacy_import,
)
from scenes.models import MutationOperation, Scene, SceneRevision
from scenes.services import create_scene
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="requires PostgreSQL"),
]


def _authority() -> tuple[Account, Workspace]:
    account = Account.objects.create_user("phase9@example.invalid", password="Synthetic-Test-Only!")
    workspace = Workspace.objects.create(name="Synthetic Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace,
        account=account,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _source(path: Path, *, title: str = "Synthetic Record") -> Path:
    value = {
        "format": FORMAT_NAME,
        "schema_version": 1,
        "scenes": [
            {
                "id": "legacy-scene-1",
                "title": title,
                "lifecycle": "archived",
                "ordering": 1024,
                "current_revision_id": "legacy-revision-2",
                "revisions": [
                    {"id": "legacy-revision-1", "sequence": 10, "content": ""},
                    {"id": "legacy-revision-2", "sequence": 20, "content": "\r\n"},
                ],
            }
        ],
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_stage_is_deterministic_idempotent_and_uses_bounded_job(tmp_path: Path) -> None:
    account, workspace = _authority()
    source = _source(tmp_path / "source.json")
    first = stage_legacy_import(account=account, workspace_id=workspace.id, source_path=source)
    second = stage_legacy_import(account=account, workspace_id=workspace.id, source_path=source)
    assert not first.replayed and second.replayed
    assert first.batch.id == second.batch.id
    assert first.batch.staged_scenes.count() == 1
    assert first.batch.staged_revisions.count() == 2
    assert first.batch.mappings.count() == 3
    job = Job.execution_objects.get(id=first.batch.staging_job_id)
    assert job.target_id == first.batch.id
    assert job.job_type == "validate_legacy_import"
    assert not hasattr(job, "content")
    assert IdempotencyRecord.execution_objects.filter(resulting_job=job).count() == 1


def test_new_target_ids_and_source_ids_are_distinct(tmp_path: Path) -> None:
    account, workspace = _authority()
    batch = stage_legacy_import(
        account=account, workspace_id=workspace.id, source_path=_source(tmp_path / "source.json")
    ).batch
    mapping = batch.mappings.get(source_entity_type=IdentityMapping.EntityType.SCENE)
    assert isinstance(mapping.target_uuid, uuid.UUID)
    assert str(mapping.target_uuid) != mapping.source_identifier


def test_owner_approval_revalidates_grant_and_staging(tmp_path: Path) -> None:
    account, workspace = _authority()
    batch = stage_legacy_import(
        account=account, workspace_id=workspace.id, source_path=_source(tmp_path / "source.json")
    ).batch
    approved = approve_import(account=account, batch_id=batch.id)
    assert approved.state == ImportBatch.State.APPROVED
    StagedRevision.objects.filter(batch=batch).update(content="changed")
    with pytest.raises(LegacyImportError):
        apply_import(
            account=account,
            batch_id=batch.id,
            source_path=tmp_path / "source.json",
            acknowledge_nonempty=False,
        )
    WorkspaceGrant.objects.filter(workspace=workspace, account=account).update(
        state=WorkspaceGrant.State.REVOKED
    )
    with pytest.raises(Http404):
        approve_import(account=account, batch_id=batch.id)


def test_apply_reconstructs_history_provenance_and_search_dispatch(tmp_path: Path) -> None:
    account, workspace = _authority()
    batch = stage_legacy_import(
        account=account, workspace_id=workspace.id, source_path=_source(tmp_path / "source.json")
    ).batch
    approve_import(account=account, batch_id=batch.id)
    applied = apply_import(
        account=account,
        batch_id=batch.id,
        source_path=tmp_path / "source.json",
        acknowledge_nonempty=False,
    )
    assert applied.state == ImportBatch.State.APPLIED
    scene = Scene.objects.get(workspace=workspace)
    assert scene.id == batch.staged_scenes.get().proposed_scene_id
    assert scene.lifecycle == Scene.Lifecycle.ARCHIVED
    assert scene.version == 2
    assert (
        scene.current_revision_id
        == batch.staged_revisions.get(is_current=True).proposed_revision_id
    )
    assert list(scene.revisions.values_list("revision_number", flat=True)) == [1, 2]
    assert (
        scene.revisions.get(revision_number=2).base_revision_id
        == scene.revisions.get(revision_number=1).id
    )
    assert MutationOperation.objects.filter(scene=scene).count() == 3
    assert ImportProvenance.objects.filter(batch=batch).count() == 3
    assert batch.mappings.filter(state=IdentityMapping.State.APPLIED).count() == 3
    assert Job.execution_objects.filter(job_type="rebuild_scene_search_projection").count() == 1
    assert apply_import(
        account=account,
        batch_id=batch.id,
        source_path=tmp_path / "source.json",
        acknowledge_nonempty=True,
    ).id


def test_nonempty_workspace_requires_acknowledgement_and_never_overwrites(tmp_path: Path) -> None:
    account, workspace = _authority()
    existing = create_scene(
        actor=account, workspace_id=workspace.id, title="Existing", ordering=2048
    ).scene
    batch = stage_legacy_import(
        account=account, workspace_id=workspace.id, source_path=_source(tmp_path / "source.json")
    ).batch
    approve_import(account=account, batch_id=batch.id)
    with pytest.raises(LegacyImportError):
        apply_import(
            account=account,
            batch_id=batch.id,
            source_path=tmp_path / "source.json",
            acknowledge_nonempty=False,
        )
    assert Scene.objects.filter(id=existing.id).exists()
    assert SceneRevision.objects.count() == 1


def test_duplicate_title_is_warning_not_merge(tmp_path: Path) -> None:
    account, workspace = _authority()
    create_scene(actor=account, workspace_id=workspace.id, title="Synthetic Record", ordering=2048)
    batch = stage_legacy_import(
        account=account, workspace_id=workspace.id, source_path=_source(tmp_path / "source.json")
    ).batch
    assert batch.findings.filter(issue_code="title_duplicate_candidate").count() == 1
    assert batch.staged_scenes.count() == 1


def test_restore_quarantine_clears_approval_and_preserves_applied(tmp_path: Path) -> None:
    account, workspace = _authority()
    batch = stage_legacy_import(
        account=account, workspace_id=workspace.id, source_path=_source(tmp_path / "source.json")
    ).batch
    approve_import(account=account, batch_id=batch.id)
    applied = ImportBatch.objects.create(
        workspace=workspace,
        source_fingerprint="a" * 64,
        source_size=1,
        requested_by=account,
        state=ImportBatch.State.APPLIED,
    )
    assert quarantine_unfinished_imports() == 1
    batch.refresh_from_db()
    applied.refresh_from_db()
    assert batch.state == ImportBatch.State.QUARANTINED
    assert batch.approved_by_id is None
    assert applied.state == ImportBatch.State.APPLIED
