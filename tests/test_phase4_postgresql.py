import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import cast
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from scenes.content import CONTENT_FORMAT_VERSION, NORMALIZATION_VERSION, content_sha256
from scenes.models import MutationOperation, Scene, SceneRevision, SceneSaveRequest
from scenes.save_requests import SaveRequestOutcome, save_scene_content
from scenes.services import create_scene
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

TEST_PASSWORD = "Synthetic-Phase4-Password-Only!"


def _owner(email: str = "phase4-owner@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=TEST_PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic Phase 4 Workspace")
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _scene(account: Account, workspace: Workspace, title: str = "Synthetic Scene") -> Scene:
    return create_scene(actor=account, workspace_id=workspace.id, title=title, ordering=None).scene


def _save_payload(scene: Scene, content: str, key: str | None = None) -> dict[str, object]:
    scene.refresh_from_db()
    return {
        "content": content,
        "expected_current_revision_id": scene.current_revision_id,
        "expected_scene_version": scene.version,
        "idempotency_key": key or uuid.uuid4().hex,
        "save_intent": "explicit_save",
    }


def _logged_in(account: Account) -> Client:
    client = Client()
    client.force_login(account)
    return client


def test_scene_list_requires_auth_and_filters_workspace_lifecycle() -> None:
    account, workspace = _owner()
    active = _scene(account, workspace, "Active Synthetic Scene")
    archived = _scene(account, workspace, "Archived Synthetic Scene")
    trashed = _scene(account, workspace, "Trashed Synthetic Scene")
    archived.lifecycle = Scene.Lifecycle.ARCHIVED
    archived.save(update_fields=("lifecycle", "updated_at"))
    trashed.lifecycle = Scene.Lifecycle.TRASHED
    trashed.save(update_fields=("lifecycle", "updated_at"))
    other_account, other_workspace = _owner("other-phase4@example.invalid")
    other = _scene(other_account, other_workspace, "Other Workspace Scene")

    assert Client().get(reverse("scene-list")).status_code == 302
    response = _logged_in(account).get(reverse("scene-list"))
    assert response.status_code == 200
    assert active.title.encode() in response.content
    assert archived.title.encode() in response.content
    assert b"Archived" in response.content
    assert trashed.title.encode() not in response.content
    assert other.title.encode() not in response.content
    assert "no-store" in response.headers["Cache-Control"]


def test_revoked_grant_immediately_denies_list_and_editor() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    client = _logged_in(account)
    grant = WorkspaceGrant.objects.get(account=account, workspace=workspace)
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))

    assert client.get(reverse("scene-list")).status_code == 404
    assert client.get(reverse("scene-editor", kwargs={"scene_id": scene.id})).status_code == 404


def test_scene_creation_is_csrf_protected_prg_and_server_scoped() -> None:
    account, workspace = _owner()
    client = _logged_in(account)
    response = client.post(
        reverse("scene-create"),
        {"title": "  Created Synthetic Scene  ", "workspace": uuid.uuid4()},
    )
    assert response.status_code == 303
    scene = Scene.objects.get(title="Created Synthetic Scene")
    assert scene.workspace == workspace
    assert response.url == reverse("scene-editor", kwargs={"scene_id": scene.id})
    assert scene.current_revision is not None

    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(account)
    assert csrf_client.post(reverse("scene-create"), {"title": "Rejected"}).status_code == 403


def test_invalid_creation_and_get_do_not_mutate() -> None:
    account, _ = _owner()
    client = _logged_in(account)
    assert client.get(reverse("scene-create")).status_code == 200
    assert Scene.objects.count() == 0
    response = client.post(reverse("scene-create"), {"title": "   "})
    assert response.status_code == 422
    assert Scene.objects.count() == 0


def test_editor_uses_current_pointer_escapes_content_and_is_private() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    current = cast(SceneRevision, scene.current_revision)
    operation = MutationOperation.objects.create(
        workspace=workspace,
        operation_type=MutationOperation.OperationType.SCENE_CONTENT_REVISED,
        source=MutationOperation.Source.OWNER,
        actor=account,
        scene=scene,
    )
    SceneRevision.objects.create(
        workspace=workspace,
        scene=scene,
        content="<script>Synthetic newer timestamp</script>",
        content_sha256=content_sha256("<script>Synthetic newer timestamp</script>"),
        revision_number=2,
        content_format_version=CONTENT_FORMAT_VERSION,
        normalization_version=NORMALIZATION_VERSION,
        base_revision=current,
        source=SceneRevision.Source.OWNER,
        actor=account,
        mutation_operation=operation,
    )

    response = _logged_in(account).get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert response.status_code == 200
    assert b"Synthetic newer timestamp" not in response.content
    assert str(current.id).encode() in response.content
    assert "no-store" in response.headers["Cache-Control"]


def test_editor_escapes_authoritative_plain_text() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "<script>Synthetic text</script>")
    client = _logged_in(account)
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    response = client.get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert b"&lt;script&gt;Synthetic text&lt;/script&gt;" in response.content
    assert b"<script>Synthetic text</script>" not in response.content


def test_archived_is_read_only_and_trashed_is_inaccessible() -> None:
    account, workspace = _owner()
    archived = _scene(account, workspace, "Archived")
    archived.lifecycle = Scene.Lifecycle.ARCHIVED
    archived.save(update_fields=("lifecycle", "updated_at"))
    trashed = _scene(account, workspace, "Trashed")
    trashed.lifecycle = Scene.Lifecycle.TRASHED
    trashed.save(update_fields=("lifecycle", "updated_at"))
    client = _logged_in(account)

    archived_response = client.get(reverse("scene-editor", kwargs={"scene_id": archived.id}))
    assert archived_response.status_code == 200
    assert b"readonly" in archived_response.content
    assert b"Save Scene" not in archived_response.content
    assert (
        client.post(
            reverse("scene-save", kwargs={"scene_id": archived.id}), _save_payload(archived, "x")
        ).status_code
        == 404
    )
    assert client.get(reverse("scene-editor", kwargs={"scene_id": trashed.id})).status_code == 404


def test_successful_save_uses_both_preconditions_and_complete_normalization() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    client = _logged_in(account)
    before_operations = MutationOperation.objects.count()
    response = client.post(
        reverse("scene-save", kwargs={"scene_id": scene.id}),
        _save_payload(scene, "Synthetic\r\ncontent"),
    )
    assert response.status_code == 303
    scene.refresh_from_db()
    assert scene.version == 2
    assert cast(SceneRevision, scene.current_revision).content == "Synthetic\ncontent"
    assert SceneRevision.objects.filter(scene=scene).count() == 2
    assert MutationOperation.objects.count() == before_operations + 1


@pytest.mark.parametrize("missing", ["expected_current_revision_id", "expected_scene_version"])
def test_save_requires_both_preconditions(missing: str) -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "Synthetic content")
    del payload[missing]
    response = _logged_in(account).post(
        reverse("scene-save", kwargs={"scene_id": scene.id}), payload
    )
    assert response.status_code == 422
    assert SceneRevision.objects.filter(scene=scene).count() == 1


@pytest.mark.parametrize("stale_field", ["expected_current_revision_id", "expected_scene_version"])
def test_stale_save_returns_escaped_conflict_without_domain_mutation(stale_field: str) -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "<b>Submitted synthetic draft</b>")
    payload[stale_field] = uuid.uuid4() if stale_field.endswith("id") else 0
    revisions = SceneRevision.objects.count()
    operations = MutationOperation.objects.count()
    response = _logged_in(account).post(
        reverse("scene-save", kwargs={"scene_id": scene.id}), payload
    )
    assert response.status_code == 409
    assert b"No changes were saved" in response.content
    assert b"&lt;b&gt;Submitted synthetic draft&lt;/b&gt;" in response.content
    assert b"force" not in response.content.lower()
    assert SceneRevision.objects.count() == revisions
    assert MutationOperation.objects.count() == operations
    assert SceneSaveRequest.objects.get().state == SceneSaveRequest.State.CONFLICTED


def test_identical_replay_returns_prior_success_without_duplicate_history() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    key = uuid.uuid4().hex
    payload = _save_payload(scene, "Synthetic replay content", key)
    client = _logged_in(account)
    first = client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload)
    second = client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload)
    assert first.status_code == second.status_code == 303
    assert SceneRevision.objects.filter(scene=scene).count() == 2
    assert MutationOperation.objects.filter(scene=scene).count() == 2
    assert SceneSaveRequest.objects.filter(scene=scene).count() == 1


@pytest.mark.parametrize(
    "changed",
    [
        {"content": "Different synthetic content"},
        {"expected_scene_version": 99},
        {"expected_current_revision_id": uuid.UUID(int=1)},
    ],
)
def test_key_reuse_with_changed_semantics_fails(changed: dict[str, object]) -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "Original synthetic content", uuid.uuid4().hex)
    client = _logged_in(account)
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    conflicting = payload | changed
    response = client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), conflicting)
    assert response.status_code == 409
    assert SceneRevision.objects.filter(scene=scene).count() == 2


def test_replay_reauthorizes_and_revoked_grant_blocks_result() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "Synthetic committed content")
    client = _logged_in(account)
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    grant = WorkspaceGrant.objects.get(account=account, workspace=workspace)
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 404
    )
    assert SceneRevision.objects.filter(scene=scene).count() == 2


def test_response_loss_reconciles_by_same_key() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "Synthetic response-loss content")
    first_client = _logged_in(account)
    assert (
        first_client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    retry_client = _logged_in(account)
    assert (
        retry_client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    assert SceneRevision.objects.filter(scene=scene).count() == 2


def test_failed_mutation_rolls_back_idempotency_reservation() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "Synthetic rollback content")
    with (
        patch("scenes.save_requests.revise_scene_content", side_effect=RuntimeError("bounded")),
        pytest.raises(RuntimeError, match="bounded"),
    ):
        save_scene_content(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=cast(uuid.UUID, scene.current_revision_id),
            expected_scene_version=scene.version,
            proposed_content=cast(str, payload["content"]),
            idempotency_key=cast(str, payload["idempotency_key"]),
            save_intent="explicit_save",
        )
    assert SceneSaveRequest.objects.filter(scene=scene).count() == 0
    assert SceneRevision.objects.filter(scene=scene).count() == 1


def test_manual_reconciliation_uses_latest_preconditions_and_new_key() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    stale = _save_payload(scene, "Stale synthetic draft", uuid.uuid4().hex)
    client = _logged_in(account)
    assert (
        client.post(
            reverse("scene-save", kwargs={"scene_id": scene.id}),
            _save_payload(scene, "First accepted synthetic change", uuid.uuid4().hex),
        ).status_code
        == 303
    )
    conflict = client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), stale)
    assert conflict.status_code == 409
    scene.refresh_from_db()
    reconciled = _save_payload(scene, "Manually reconciled synthetic content", uuid.uuid4().hex)
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), reconciled).status_code
        == 303
    )
    scene.refresh_from_db()
    assert cast(SceneRevision, scene.current_revision).content == (
        "Manually reconciled synthetic content"
    )


def test_cross_workspace_malformed_get_and_csrf_fail_safely() -> None:
    account, _ = _owner()
    other, other_workspace = _owner("other-access@example.invalid")
    scene = _scene(other, other_workspace)
    client = _logged_in(account)
    assert client.get(reverse("scene-editor", kwargs={"scene_id": scene.id})).status_code == 404
    assert client.get(reverse("scene-save", kwargs={"scene_id": scene.id})).status_code == 405

    own_workspace = Workspace.objects.get(grants__account=account)
    own_scene = _scene(account, own_workspace)
    malformed = _save_payload(own_scene, "Synthetic")
    malformed["expected_current_revision_id"] = "not-a-uuid"
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": own_scene.id}), malformed).status_code
        == 422
    )
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(account)
    assert (
        csrf_client.post(
            reverse("scene-save", kwargs={"scene_id": own_scene.id}),
            _save_payload(own_scene, "Synthetic"),
        ).status_code
        == 403
    )


def test_oversized_content_is_rejected_without_revision() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    payload = _save_payload(scene, "x" * 1_000_001)
    response = _logged_in(account).post(
        reverse("scene-save", kwargs={"scene_id": scene.id}), payload
    )
    assert response.status_code == 422
    assert SceneRevision.objects.filter(scene=scene).count() == 1


def test_concurrent_identical_save_requests_converge() -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    current = cast(SceneRevision, scene.current_revision)
    key = uuid.uuid4().hex
    barrier = threading.Barrier(2)

    def execute() -> SaveRequestOutcome:
        close_old_connections()
        try:
            worker_account = Account.objects.get(id=account.id)
            barrier.wait(timeout=5)
            result = save_scene_content(
                actor=worker_account,
                workspace_id=workspace.id,
                scene_id=scene.id,
                expected_current_revision_id=current.id,
                expected_scene_version=scene.version,
                proposed_content="Concurrent synthetic content",
                idempotency_key=key,
                save_intent="explicit_save",
            )
            return result.outcome
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: execute(), range(2)))
    assert outcomes == [SaveRequestOutcome.SUCCEEDED, SaveRequestOutcome.SUCCEEDED]
    assert SceneRevision.objects.filter(scene=scene).count() == 2
    assert MutationOperation.objects.filter(scene=scene).count() == 2
    assert SceneSaveRequest.objects.filter(scene=scene).count() == 1
