import os
import uuid
from io import StringIO

import pytest
from django.core.management import call_command
from django.http import Http404
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from jobs.models import Job
from jobs.services import claim_jobs, execute_claim
from scenes.exceptions import OptimisticConcurrencyConflict
from scenes.models import MutationOperation, Scene, SceneRevision, SceneSearchProjection
from scenes.search import search_scenes
from scenes.services import create_scene, revise_scene_content
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL search tests.",
    ),
]

PASSWORD = "Synthetic-Phase7-Password-Only!"


def _owner(email: str = "phase7@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic Search Workspace")
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _scene(account: Account, workspace: Workspace, title: str = "Synthetic Search Title") -> Scene:
    return create_scene(actor=account, workspace_id=workspace.id, title=title).scene


def _save(account: Account, workspace: Workspace, scene: Scene, content: str) -> Scene:
    scene.refresh_from_db()
    result = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content=content,
    )
    return result.scene


def _run_all_jobs() -> None:
    while claimed := claim_jobs(worker_id="search-test-worker", batch_size=20):
        for item in claimed:
            execute_claim(item)


def test_creation_enqueues_and_handler_builds_current_projection() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    job = Job.objects.get(job_type="rebuild_scene_search_projection")
    assert job.target_id == scene.id
    assert job.expected_revision_id == scene.current_revision_id
    assert not SceneSearchProjection.objects.exists()
    _run_all_jobs()
    projection = SceneSearchProjection.objects.get(scene=scene)
    assert projection.source_revision_id == scene.current_revision_id
    assert projection.source_scene_version == scene.version


def test_content_save_invalidates_projection_and_enqueues_atomically() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    _run_all_jobs()
    assert SceneSearchProjection.objects.filter(scene=scene).exists()
    previous_jobs = Job.objects.count()
    scene = _save(account, workspace, scene, "Synthetic searchable needle")
    assert not SceneSearchProjection.objects.filter(scene=scene).exists()
    assert Job.objects.count() == previous_jobs + 1
    _run_all_jobs()
    assert SceneSearchProjection.objects.get(scene=scene).source_scene_version == scene.version


def test_stale_conflict_creates_no_search_job() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    jobs = Job.objects.count()
    revisions = SceneRevision.objects.count()
    operations = MutationOperation.objects.count()
    with pytest.raises(OptimisticConcurrencyConflict):
        revise_scene_content(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=uuid.uuid4(),
            expected_scene_version=scene.version,
            proposed_content="Synthetic stale text",
        )
    assert Job.objects.count() == jobs
    assert SceneRevision.objects.count() == revisions
    assert MutationOperation.objects.count() == operations


def test_old_worker_cannot_overwrite_newer_projection() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    old_claim = claim_jobs(worker_id="old-search-worker")[0]
    scene = _save(account, workspace, scene, "newer searchable marker")
    execute_claim(old_claim)
    assert not SceneSearchProjection.objects.filter(scene=scene).exists()
    _run_all_jobs()
    assert SceneSearchProjection.objects.get(scene=scene).source_scene_version == scene.version


def test_search_authorization_lifecycle_and_stale_omission() -> None:
    account, workspace = _owner()
    active = _scene(account, workspace, "Active marker")
    archived = _scene(account, workspace, "Archived marker")
    trashed = _scene(account, workspace, "Trashed marker")
    active = _save(account, workspace, active, "shared needle")
    archived = _save(account, workspace, archived, "shared needle")
    trashed = _save(account, workspace, trashed, "shared needle")
    Scene.objects.filter(id=archived.id).update(lifecycle=Scene.Lifecycle.ARCHIVED)
    Scene.objects.filter(id=trashed.id).update(lifecycle=Scene.Lifecycle.TRASHED)
    _run_all_jobs()
    assert [
        item.scene.id
        for item in search_scenes(actor=account, workspace_id=workspace.id, query_text="needle")
    ] == [active.id]
    included = search_scenes(
        actor=account, workspace_id=workspace.id, query_text="needle", include_archived=True
    )
    assert {item.scene.id for item in included} == {active.id, archived.id}
    projection = SceneSearchProjection.objects.get(scene=active)
    projection.source_scene_version = active.version - 1
    projection.save(update_fields=("source_scene_version",))
    assert search_scenes(actor=account, workspace_id=workspace.id, query_text="needle") == []


def test_revoked_grant_and_other_workspace_never_search() -> None:
    account, workspace = _owner()
    scene = _save(account, workspace, _scene(account, workspace), "private needle")
    _run_all_jobs()
    other, other_workspace = _owner("other-phase7@example.invalid")
    assert search_scenes(actor=other, workspace_id=other_workspace.id, query_text="needle") == []
    grant = WorkspaceGrant.objects.get(account=account, workspace=workspace)
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))
    with pytest.raises(Http404):
        search_scenes(actor=account, workspace_id=workspace.id, query_text="needle")
    assert scene.workspace_id == workspace.id


def test_blank_oversized_and_limit_validation() -> None:
    account, workspace = _owner()
    assert search_scenes(actor=account, workspace_id=workspace.id, query_text="  ") == []
    with pytest.raises(ValueError):
        search_scenes(actor=account, workspace_id=workspace.id, query_text="x" * 201)
    with pytest.raises(ValueError):
        search_scenes(actor=account, workspace_id=workspace.id, query_text="x", limit=51)


def test_private_post_search_is_csrf_protected_escaped_and_no_store() -> None:
    account, workspace = _owner()
    _save(account, workspace, _scene(account, workspace, "<b>Synthetic</b>"), "needle text")
    _run_all_jobs()
    client = Client()
    client.force_login(account)
    response = client.post(reverse("scene-search"), {"query": "needle"})
    assert response.status_code == 200
    assert b"&lt;b&gt;Synthetic&lt;/b&gt;" in response.content
    assert "no-store" in response.headers["Cache-Control"]
    assert "?" not in response.request["PATH_INFO"]
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(account)
    assert csrf_client.post(reverse("scene-search"), {"query": "needle"}).status_code == 403


def test_commands_are_bounded_and_reset_only_derived_rows() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    _run_all_jobs()
    revisions = SceneRevision.objects.count()
    dry = StringIO()
    call_command("enqueue_search_rebuild", workspace=str(workspace.id), dry_run=True, stdout=dry)
    assert "planned=" in dry.getvalue()
    output = StringIO()
    call_command(
        "reset_search_projections",
        workspace=str(workspace.id),
        confirm=True,
        stdout=output,
    )
    assert not SceneSearchProjection.objects.exists()
    assert Scene.objects.filter(id=scene.id).exists()
    assert SceneRevision.objects.count() == revisions
    assert "search_projections reset=" in output.getvalue()
