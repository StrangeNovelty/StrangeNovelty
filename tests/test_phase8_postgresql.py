import os
from pathlib import Path

import pytest
from django.core.management import call_command

from accounts.models import Account
from archives.services import (
    ArchiveError,
    export_readable_workspace,
    export_workspace_archive,
    restore_workspace_archive,
    validate_workspace_archive,
    verify_restore_readiness,
)
from jobs.models import Job
from scenes.models import Scene, SceneRevision, SceneSearchProjection
from scenes.services import create_scene, revise_scene_content
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for archive/restore integration tests.",
    ),
]

PASSWORD = "Synthetic-Phase8-Password-Only!"


def _domain() -> tuple[Account, Workspace, Scene]:
    account = Account.objects.create_user("phase8@example.invalid", password=PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic Archive Workspace")
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    scene = create_scene(
        actor=account, workspace_id=workspace.id, title="Synthetic Archive Scene"
    ).scene
    scene.refresh_from_db()
    scene = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="Synthetic archive content",
    ).scene
    return account, workspace, scene


def test_readable_export_uses_current_pointer_safe_names_and_utf8(tmp_path: Path) -> None:
    _account, workspace, scene = _domain()
    output = tmp_path / "readable"
    assert export_readable_workspace(workspace.id, output) == 1
    files = list((output / "scenes").iterdir())
    assert len(files) == 1
    assert scene.id.hex in files[0].name
    assert "Synthetic archive content" in files[0].read_text(encoding="utf-8")
    assert (output / "index.txt").exists()
    with pytest.raises(ArchiveError, match="exists"):
        export_readable_workspace(workspace.id, output)


def test_structured_archive_preserves_history_and_excludes_operations_state(tmp_path: Path) -> None:
    _account, workspace, scene = _domain()
    archive = tmp_path / "archive"
    counts = export_workspace_archive(workspace.id, archive)
    validation = validate_workspace_archive(archive)
    assert counts["revisions"] == 2
    assert validation.manifest["source_workspace_id"] == str(workspace.id)
    assert len(validation.records["revisions"]) == 2
    assert validation.records["scenes"][0]["current_revision_id"] == str(scene.current_revision_id)
    combined = "\n".join(path.read_text() for path in archive.rglob("*.json"))
    for excluded in ("password_hash", "session_key", "search_projection", "idempotency_key"):
        assert excluded not in combined
    assert Job.objects.exists()
    assert not any("job" in item["path"] for item in validation.manifest["files"])


def test_tamper_missing_and_symlink_validation_fail(tmp_path: Path) -> None:
    _account, workspace, _scene = _domain()
    archive = tmp_path / "archive"
    export_workspace_archive(workspace.id, archive)
    revisions = archive / "records/revisions.json"
    revisions.write_text(revisions.read_text() + " ")
    with pytest.raises(ArchiveError, match="integrity"):
        validate_workspace_archive(archive)


def test_restore_dry_run_and_nonempty_target_rejection(tmp_path: Path) -> None:
    _account, workspace, _scene = _domain()
    archive = tmp_path / "archive"
    export_workspace_archive(workspace.id, archive)
    with pytest.raises(ArchiveError, match="empty"):
        restore_workspace_archive(
            archive,
            tmp_path / "report.json",
            dry_run=True,
            confirmed=False,
            isolated_acknowledged=False,
        )


def test_identity_preserving_restore_revokes_grants_and_writes_report(tmp_path: Path) -> None:
    account, workspace, scene = _domain()
    account_id, workspace_id, scene_id = account.id, workspace.id, scene.id
    revision_ids = set(SceneRevision.objects.values_list("id", flat=True))
    archive = tmp_path / "archive"
    export_workspace_archive(workspace.id, archive)
    call_command("flush", interactive=False, verbosity=0)
    Account.objects.create_user(
        "restored-operator@example.invalid", password=PASSWORD, id=account_id
    )
    report_path = tmp_path / "verification.json"
    report = restore_workspace_archive(
        archive, report_path, dry_run=False, confirmed=True, isolated_acknowledged=True
    )
    assert Workspace.objects.get().id == workspace_id
    assert Scene.objects.get().id == scene_id
    assert set(SceneRevision.objects.values_list("id", flat=True)) == revision_ids
    assert WorkspaceGrant.objects.get().state == WorkspaceGrant.State.REVOKED
    assert report["identity_preserved"]
    assert verify_restore_readiness(report_path, operational_checks_acknowledged=True)
    assert not SceneSearchProjection.objects.exists()


def test_commands_print_counts_not_private_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _account, workspace, _scene = _domain()
    archive = tmp_path / "archive"
    call_command("export_workspace_archive", workspace=str(workspace.id), output=str(archive))
    call_command("validate_workspace_archive", archive=str(archive))
    output = capsys.readouterr().out
    assert "records=" in output
    assert "Synthetic Archive" not in output
    assert "Synthetic archive content" not in output
