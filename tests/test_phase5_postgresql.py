import os
import uuid
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from scenes.models import MutationOperation, Scene, SceneRevision, SceneSaveRequest
from scenes.services import create_scene
from security_events.exceptions import ImmutableSecurityEventError
from security_events.models import SecurityEvent
from security_events.services import SecurityEventSpec, record_security_event
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)
from workspaces.models import OwnerBootstrap, Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

TEST_PASSWORD = "Synthetic-Phase5-Password-Only!"


def _owner(email: str = "phase5-owner@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=TEST_PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic Phase 5 Workspace")
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _scene(account: Account, workspace: Workspace) -> Scene:
    return create_scene(
        actor=account,
        workspace_id=workspace.id,
        title="Synthetic Security Scene",
        ordering=None,
    ).scene


def _payload(scene: Scene, content: str, key: str | None = None) -> dict[str, object]:
    scene.refresh_from_db()
    return {
        "content": content,
        "expected_current_revision_id": scene.current_revision_id,
        "expected_scene_version": scene.version,
        "idempotency_key": key or uuid.uuid4().hex,
        "save_intent": "explicit_save",
    }


def test_security_event_creation_references_are_protected_and_immutable() -> None:
    account, workspace = _owner()
    event = record_security_event(
        SecurityEventSpec(
            event_type=SecurityEventType.LOGIN_SUCCEEDED,
            outcome=SecurityOutcome.SUCCEEDED,
            actor=account,
            workspace=workspace,
            target_category=SecurityTargetCategory.AUTHENTICATION,
            correlation_id=uuid.uuid4().hex,
            service_role=SecurityServiceRole.WEB,
        ),
        required=True,
    )
    assert event is not None
    with pytest.raises(ImmutableSecurityEventError):
        SecurityEvent.objects.filter(id=event.id).update(outcome=SecurityOutcome.FAILED)
    with pytest.raises(ImmutableSecurityEventError):
        SecurityEvent.objects.filter(id=event.id).delete()
    with pytest.raises(ProtectedError):
        account.delete()
    with pytest.raises(ProtectedError):
        workspace.delete()


def test_successful_login_records_known_actor_without_credentials(client: Client) -> None:
    account, workspace = _owner()
    response = client.post(reverse("login"), {"username": account.email, "password": TEST_PASSWORD})
    assert response.status_code == 302
    event = SecurityEvent.objects.get(event_type=SecurityEventType.LOGIN_SUCCEEDED)
    assert event.actor == account
    assert event.workspace == workspace
    assert event.target_category == SecurityTargetCategory.AUTHENTICATION
    assert not hasattr(event, "password")
    assert not hasattr(event, "session")


def test_unknown_invalid_and_inactive_login_are_generic_and_store_no_input(client: Client) -> None:
    inactive, _ = _owner("inactive-phase5@example.invalid")
    inactive.is_active = False
    inactive.save(update_fields=("is_active",))
    responses = [
        client.post(
            reverse("login"),
            {"username": "unknown-phase5@example.invalid", "password": TEST_PASSWORD},
        ),
        client.post(
            reverse("login"),
            {"username": inactive.email, "password": TEST_PASSWORD},
        ),
    ]
    assert all(
        b"Unable to sign in with those credentials." in response.content for response in responses
    )
    events = SecurityEvent.objects.filter(event_type=SecurityEventType.LOGIN_FAILED)
    assert events.count() == 2
    assert all(event.actor_id is None and event.workspace_id is None for event in events)
    assert all(event.reason == SecurityReason.INVALID_CREDENTIALS for event in events)


def test_logout_records_event_and_flushes_session(client: Client) -> None:
    account, workspace = _owner()
    client.force_login(account)
    response = client.post(reverse("logout"))
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session
    event = SecurityEvent.objects.get(event_type=SecurityEventType.LOGOUT_SUCCEEDED)
    assert event.actor == account
    assert event.workspace == workspace
    assert event.target_category == SecurityTargetCategory.SESSION


def test_bootstrap_success_event_is_atomic_and_exact_rerun_is_quiet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD", TEST_PASSWORD)
    arguments = {
        "email": "phase5-bootstrap@example.invalid",
        "workspace_name": "Synthetic Bootstrap Workspace",
        "no_input": True,
        "stdout": StringIO(),
    }
    call_command("bootstrap_owner", **arguments)
    assert Account.objects.count() == Workspace.objects.count() == 1
    assert WorkspaceGrant.objects.count() == OwnerBootstrap.objects.count() == 1
    event = SecurityEvent.objects.get(event_type=SecurityEventType.OWNER_BOOTSTRAP_SUCCEEDED)
    assert event.actor_id is not None and event.workspace_id is not None
    call_command("bootstrap_owner", **arguments)
    assert SecurityEvent.objects.count() == 1


def test_bootstrap_conflict_records_bounded_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD", TEST_PASSWORD)
    call_command(
        "bootstrap_owner",
        email="phase5-bootstrap@example.invalid",
        workspace_name="Synthetic Bootstrap Workspace",
        no_input=True,
        stdout=StringIO(),
    )
    with pytest.raises(CommandError, match="conflicts"):
        call_command(
            "bootstrap_owner",
            email="different-phase5@example.invalid",
            workspace_name="Different Synthetic Workspace",
            no_input=True,
            stdout=StringIO(),
        )
    rejected = SecurityEvent.objects.get(event_type=SecurityEventType.OWNER_BOOTSTRAP_REJECTED)
    assert rejected.reason == SecurityReason.EXISTING_STATE


def test_required_bootstrap_evidence_failure_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD", TEST_PASSWORD)
    with (
        patch.object(SecurityEvent.objects, "create", side_effect=DatabaseError("bounded")),
        pytest.raises(DatabaseError),
    ):
        call_command(
            "bootstrap_owner",
            email="phase5-bootstrap@example.invalid",
            workspace_name="Synthetic Bootstrap Workspace",
            no_input=True,
            stdout=StringIO(),
        )
    assert Account.objects.count() == 0
    assert Workspace.objects.count() == 0
    assert WorkspaceGrant.objects.count() == 0
    assert OwnerBootstrap.objects.count() == 0


def test_revoked_workspace_access_records_bounded_denial(client: Client) -> None:
    account, workspace = _owner()
    grant = WorkspaceGrant.objects.get(account=account, workspace=workspace)
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))
    client.force_login(account)
    response = client.get(reverse("workspace-home"))
    assert response.status_code == 404
    event = SecurityEvent.objects.get(event_type=SecurityEventType.WORKSPACE_ACCESS_DENIED)
    assert event.actor == account
    assert event.workspace_id is None
    assert event.target_id is None
    assert event.reason == SecurityReason.INACCESSIBLE


def test_denial_event_failure_does_not_change_safe_denial(client: Client) -> None:
    account, workspace = _owner()
    grant = WorkspaceGrant.objects.get(account=account, workspace=workspace)
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))
    client.force_login(account)
    with patch("workspaces.views.record_security_event", return_value=None):
        response = client.get(reverse("workspace-home"))
    assert response.status_code == 404


def test_cross_workspace_scene_denial_does_not_record_target_identifier(client: Client) -> None:
    account, _ = _owner()
    other, other_workspace = _owner("other-phase5@example.invalid")
    scene = _scene(other, other_workspace)
    client.force_login(account)
    response = client.get(
        reverse("scene-editor", kwargs={"scene_id": scene.id}),
        HTTP_X_REQUEST_ID=scene.id.hex,
    )
    assert response.status_code == 404
    assert response.headers["X-Request-ID"] != scene.id.hex
    event = SecurityEvent.objects.get(event_type=SecurityEventType.SCENE_ACCESS_DENIED)
    assert event.target_id is None
    assert event.workspace_id is not None


def test_concurrency_conflict_records_security_event_not_domain_provenance(client: Client) -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    client.force_login(account)
    payload = _payload(scene, "Synthetic stale security text")
    payload["expected_scene_version"] = 0
    revisions = SceneRevision.objects.count()
    operations = MutationOperation.objects.count()
    response = client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload)
    assert response.status_code == 409
    assert SceneRevision.objects.count() == revisions
    assert MutationOperation.objects.count() == operations
    event = SecurityEvent.objects.get(event_type=SecurityEventType.SCENE_SAVE_CONFLICT)
    assert event.reason == SecurityReason.OPTIMISTIC_CONCURRENCY
    assert event.target_id == scene.id


def test_key_conflict_records_security_event_without_duplicate_mutation(client: Client) -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    client.force_login(account)
    key = uuid.uuid4().hex
    payload = _payload(scene, "Synthetic accepted security text", key)
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    changed = payload | {"content": "Different synthetic security text"}
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), changed).status_code
        == 409
    )
    assert SceneRevision.objects.filter(scene=scene).count() == 2
    assert MutationOperation.objects.filter(scene=scene).count() == 2
    event = SecurityEvent.objects.get(event_type=SecurityEventType.SCENE_SAVE_KEY_CONFLICT)
    assert event.reason == SecurityReason.IDEMPOTENCY_KEY_REUSE


def test_successful_save_and_replay_use_mutation_operation_not_security_event(
    client: Client,
) -> None:
    account, workspace = _owner()
    scene = _scene(account, workspace)
    client.force_login(account)
    payload = _payload(scene, "Synthetic successful security text")
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    assert (
        client.post(reverse("scene-save", kwargs={"scene_id": scene.id}), payload).status_code
        == 303
    )
    assert MutationOperation.objects.filter(scene=scene).count() == 2
    assert SceneSaveRequest.objects.filter(scene=scene).count() == 1
    assert SecurityEvent.objects.count() == 0
