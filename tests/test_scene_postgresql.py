import os
import uuid
from typing import cast
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Account
from scenes.content import (
    CONTENT_FORMAT_VERSION,
    NORMALIZATION_VERSION,
    content_sha256,
)
from scenes.exceptions import (
    ImmutableMutationOperationError,
    ImmutableRevisionError,
    LifecycleDisallowsMutation,
    NotAuthenticated,
    OptimisticConcurrencyConflict,
    SceneInaccessible,
)
from scenes.models import MutationOperation, Scene, SceneRevision
from scenes.services import create_scene, revise_scene_content
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

TEST_PASSWORD = "Synthetic-Phase3-Password-Only!"


def _account(email: str = "owner@example.invalid") -> Account:
    return Account.objects.create_user(email, password=TEST_PASSWORD)


def _workspace(account: Account, name: str = "Synthetic Workspace") -> Workspace:
    workspace = cast(Workspace, Workspace.objects.create(name=name))
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return workspace


def _scene(account: Account, workspace: Workspace, ordering: int = 1000) -> Scene:
    return create_scene(
        actor=account,
        workspace_id=workspace.id,
        title="  Synthetic Scene  ",
        ordering=ordering,
    ).scene


def test_scene_creation_is_atomic_complete_and_workspace_scoped() -> None:
    account = _account()
    workspace = _workspace(account)

    result = create_scene(
        actor=account,
        workspace_id=workspace.id,
        title="  Synthetic Scene  ",
        ordering=1000,
    )

    result.scene.refresh_from_db()
    assert Scene.objects.count() == 1
    assert SceneRevision.objects.count() == 1
    assert MutationOperation.objects.count() == 1
    assert result.scene.workspace == workspace
    assert result.scene.title == "Synthetic Scene"
    assert result.scene.lifecycle == Scene.Lifecycle.ACTIVE
    assert result.scene.ordering == 1000
    assert result.scene.version == 1
    assert result.scene.current_revision == result.revision
    assert result.revision.content == ""
    assert result.revision.revision_number == 1
    assert result.revision.base_revision is None
    assert result.revision.workspace == workspace
    assert result.revision.scene == result.scene
    assert result.revision.content_format_version == CONTENT_FORMAT_VERSION
    assert result.revision.normalization_version == NORMALIZATION_VERSION
    assert result.revision.content_sha256 == content_sha256("")
    assert result.operation.operation_type == MutationOperation.OperationType.SCENE_CREATED
    assert result.operation.actor == account
    assert result.operation.scene == result.scene


def test_scene_creation_requires_current_active_grant() -> None:
    account = _account()
    workspace = _workspace(account)
    grant = WorkspaceGrant.objects.get(account=account, workspace=workspace)
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))

    with pytest.raises(SceneInaccessible):
        _scene(account, workspace)
    with pytest.raises(NotAuthenticated):
        create_scene(
            actor=Account(),
            workspace_id=workspace.id,
            title="Synthetic Scene",
            ordering=1000,
        )


def test_scene_creation_failure_rolls_back_every_record() -> None:
    account = _account()
    workspace = _workspace(account)

    with (
        patch.object(SceneRevision.objects, "create", side_effect=RuntimeError("synthetic")),
        pytest.raises(RuntimeError, match="synthetic"),
    ):
        _scene(account, workspace)

    assert Scene.objects.count() == 0
    assert SceneRevision.objects.count() == 0
    assert MutationOperation.objects.count() == 0


def test_complete_content_revision_normalizes_and_advances_once() -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    previous = scene.current_revision
    assert previous is not None

    result = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=previous.id,
        expected_scene_version=scene.version,
        proposed_content="  Cafe\u0301\r\nSecond line  ",
    )

    result.scene.refresh_from_db()
    previous.refresh_from_db()
    assert result.revision.content == "  Café\nSecond line  "
    assert result.revision.revision_number == 2
    assert result.revision.base_revision == previous
    assert result.revision.restored_from is None
    assert result.scene.current_revision == result.revision
    assert result.scene.version == 2
    assert previous.content == ""
    assert SceneRevision.objects.count() == 2
    assert MutationOperation.objects.count() == 2
    assert result.operation.operation_type == (
        MutationOperation.OperationType.SCENE_CONTENT_REVISED
    )


@pytest.mark.parametrize("stale_part", ["revision", "version", "both"])
def test_both_concurrency_preconditions_must_match_without_side_effects(
    stale_part: str,
) -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    current = scene.current_revision
    assert current is not None
    expected_revision = uuid.uuid4() if stale_part in {"revision", "both"} else current.id
    expected_version = scene.version - 1 if stale_part in {"version", "both"} else scene.version

    with pytest.raises(OptimisticConcurrencyConflict) as conflict:
        revise_scene_content(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=expected_revision,
            expected_scene_version=expected_version,
            proposed_content="Rejected synthetic draft",
        )

    assert conflict.value.current_revision_id == current.id
    assert conflict.value.current_scene_version == scene.version
    assert SceneRevision.objects.count() == 1
    assert MutationOperation.objects.count() == 1
    scene.refresh_from_db()
    assert scene.current_revision == current


def test_competing_retry_cannot_silently_overwrite() -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    current = scene.current_revision
    assert current is not None
    observed_version = scene.version

    revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=current.id,
        expected_scene_version=observed_version,
        proposed_content="First accepted value",
    )
    with pytest.raises(OptimisticConcurrencyConflict):
        revise_scene_content(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=current.id,
            expected_scene_version=observed_version,
            proposed_content="Competing value",
        )

    scene.refresh_from_db()
    assert scene.current_revision is not None
    assert scene.current_revision.content == "First accepted value"
    assert SceneRevision.objects.count() == 2


@pytest.mark.parametrize("lifecycle", [Scene.Lifecycle.ARCHIVED, Scene.Lifecycle.TRASHED])
def test_non_active_scenes_reject_ordinary_content_mutation(lifecycle: str) -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    current = scene.current_revision
    assert current is not None
    scene.lifecycle = lifecycle
    scene.save(update_fields=("lifecycle", "updated_at"))

    with pytest.raises(LifecycleDisallowsMutation):
        revise_scene_content(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=current.id,
            expected_scene_version=scene.version,
            proposed_content="Rejected value",
        )

    assert SceneRevision.objects.count() == 1


def test_cross_workspace_scene_and_revoked_grant_are_denied() -> None:
    account = _account()
    workspace = _workspace(account)
    other = Workspace.objects.create(name="Other Synthetic Workspace")
    other_account = _account("other@example.invalid")
    WorkspaceGrant.objects.create(
        account=other_account,
        workspace=other,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    scene = _scene(other_account, other)
    current = scene.current_revision
    assert current is not None

    with pytest.raises(SceneInaccessible):
        revise_scene_content(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=current.id,
            expected_scene_version=scene.version,
            proposed_content="Rejected value",
        )


def test_revision_instance_queryset_and_operation_are_immutable() -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    revision = scene.current_revision
    assert revision is not None
    operation = revision.mutation_operation

    revision.content = "Changed"
    with pytest.raises(ImmutableRevisionError):
        revision.save()
    with pytest.raises(ImmutableRevisionError):
        SceneRevision.objects.filter(id=revision.id).update(content="Changed")
    with pytest.raises(ImmutableRevisionError):
        revision.delete()

    operation.source = "changed"
    with pytest.raises(ImmutableMutationOperationError):
        operation.save()
    with pytest.raises(ImmutableMutationOperationError):
        MutationOperation.objects.filter(id=operation.id).delete()


def test_revision_scope_lineage_and_operation_validation() -> None:
    account = _account()
    first_workspace = _workspace(account)
    second_account = _account("second@example.invalid")
    second_workspace = _workspace(second_account, "Second Synthetic Workspace")
    first_scene = _scene(account, first_workspace)
    second_scene = _scene(second_account, second_workspace)
    first_revision = first_scene.current_revision
    second_revision = second_scene.current_revision
    assert first_revision is not None
    assert second_revision is not None

    invalid = SceneRevision(
        workspace=first_workspace,
        scene=first_scene,
        content="Synthetic",
        content_sha256=content_sha256("Synthetic"),
        revision_number=2,
        base_revision=second_revision,
        source=SceneRevision.Source.OWNER,
        actor=account,
        mutation_operation=first_revision.mutation_operation,
    )
    with pytest.raises(ValidationError, match="same Scene and Workspace"):
        invalid.clean()

    first_scene.current_revision = second_revision
    with pytest.raises(ValidationError, match="Current Revision"):
        first_scene.clean()


def test_database_constraints_cover_revision_numbers_order_and_version() -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    current = scene.current_revision
    assert current is not None

    with pytest.raises(IntegrityError), transaction.atomic():
        Scene.objects.create(
            workspace=workspace,
            title="Duplicate Order",
            lifecycle=Scene.Lifecycle.ACTIVE,
            ordering=scene.ordering,
            version=0,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Scene.objects.filter(id=scene.id).update(version=-1)

    operation = MutationOperation.objects.create(
        workspace=workspace,
        operation_type=MutationOperation.OperationType.SCENE_CONTENT_REVISED,
        actor=account,
        scene=scene,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        SceneRevision.objects.create(
            workspace=workspace,
            scene=scene,
            content="Duplicate number",
            content_sha256=content_sha256("Duplicate number"),
            revision_number=current.revision_number,
            base_revision=current,
            actor=account,
            mutation_operation=operation,
        )


def test_no_automatic_merge_or_idempotency_claim_exists() -> None:
    account = _account()
    workspace = _workspace(account)
    scene = _scene(account, workspace)
    current = scene.current_revision
    assert current is not None

    result = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=current.id,
        expected_scene_version=scene.version,
        proposed_content="Complete replacement snapshot",
    )

    assert result.revision.content == "Complete replacement snapshot"
    assert not hasattr(result.operation, "idempotency_key")
    assert not hasattr(result.revision, "patch")
