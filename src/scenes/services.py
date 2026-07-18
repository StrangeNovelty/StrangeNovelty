import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.http import Http404

from accounts.models import Account
from scenes.content import (
    CONTENT_FORMAT_VERSION,
    MAX_CONTENT_CHARACTERS,
    NORMALIZATION_VERSION,
    content_sha256,
    normalize_scene_content,
)
from scenes.exceptions import (
    CrossWorkspaceReference,
    DomainIntegrityFailure,
    InvalidSceneOrdering,
    InvalidSceneTitle,
    LifecycleDisallowsMutation,
    NotAuthenticated,
    OptimisticConcurrencyConflict,
    SceneInaccessible,
)
from scenes.models import MutationOperation, Scene, SceneRevision
from workspaces.models import Workspace, WorkspaceGrant
from workspaces.services import get_authorized_workspace

MAX_TITLE_CHARACTERS = 200


class SceneMutationIntent(StrEnum):
    CONTENT_REVISION = "content_revision"


@dataclass(frozen=True, slots=True)
class SceneMutationResult:
    scene: Scene
    revision: SceneRevision
    operation: MutationOperation


def validate_scene_title(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidSceneTitle("Scene title must be text.")
    title = value.strip()
    if not title or "\x00" in title or len(title) > MAX_TITLE_CHARACTERS:
        raise InvalidSceneTitle("Scene title is invalid.")
    return title


def validate_scene_ordering(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidSceneOrdering("Scene ordering must be a non-negative integer.")
    return value


def create_scene(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    title: str,
    ordering: int | None = None,
) -> SceneMutationResult:
    normalized_title = validate_scene_title(title)
    normalized_content = normalize_scene_content("")

    with transaction.atomic():
        workspace = lock_authorized_workspace(actor, workspace_id)
        if ordering is None:
            highest_order = Scene.objects.filter(workspace=workspace).aggregate(
                highest=models.Max("ordering")
            )["highest"]
            normalized_ordering = 1024 if highest_order is None else highest_order + 1024
        else:
            normalized_ordering = validate_scene_ordering(ordering)
        try:
            scene = Scene.objects.create(
                workspace=workspace,
                title=normalized_title,
                lifecycle=Scene.Lifecycle.ACTIVE,
                ordering=normalized_ordering,
                version=0,
                current_revision=None,
            )
            operation = MutationOperation.objects.create(
                workspace=workspace,
                operation_type=MutationOperation.OperationType.SCENE_CREATED,
                source=MutationOperation.Source.OWNER,
                actor=actor,
                scene=scene,
            )
            revision = SceneRevision.objects.create(
                workspace=workspace,
                scene=scene,
                content=normalized_content,
                content_sha256=content_sha256(normalized_content),
                revision_number=1,
                content_format_version=CONTENT_FORMAT_VERSION,
                normalization_version=NORMALIZATION_VERSION,
                base_revision=None,
                restored_from=None,
                source=SceneRevision.Source.OWNER,
                actor=actor,
                mutation_operation=operation,
            )
            scene.current_revision = revision
            scene.version = 1
            scene.full_clean()
            scene.save(update_fields=("current_revision", "version", "updated_at"))
            from scenes.search_indexing import invalidate_and_enqueue_scene_search

            invalidate_and_enqueue_scene_search(scene, revision)
            from stories.workshop import record_writing_delta

            record_writing_delta(scene=scene, revision=revision)
        except (IntegrityError, ValidationError) as exc:
            raise DomainIntegrityFailure(
                "Scene creation could not preserve domain integrity."
            ) from exc

    return SceneMutationResult(scene=scene, revision=revision, operation=operation)


def revise_scene_content(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    scene_id: uuid.UUID,
    expected_current_revision_id: uuid.UUID,
    expected_scene_version: int,
    proposed_content: str,
    intent: SceneMutationIntent = SceneMutationIntent.CONTENT_REVISION,
) -> SceneMutationResult:
    if intent is not SceneMutationIntent.CONTENT_REVISION:
        raise DomainIntegrityFailure("Unsupported Scene mutation intent.")
    normalized_content = normalize_scene_content(proposed_content)

    with transaction.atomic():
        workspace = lock_authorized_workspace(actor, workspace_id)
        try:
            scene = cast(
                Scene,
                Scene.objects.select_for_update(of=("self",))
                .select_related("current_revision")
                .get(id=scene_id, workspace=workspace),
            )
        except Scene.DoesNotExist as exc:
            raise SceneInaccessible("Scene is unavailable.") from exc

        if scene.lifecycle != Scene.Lifecycle.ACTIVE:
            raise LifecycleDisallowsMutation(
                "Only active Scenes accept ordinary content revisions."
            )
        current = scene.current_revision
        if current is None:
            raise DomainIntegrityFailure("Scene has no current Revision.")
        if current.workspace_id != workspace.id or current.scene_id != scene.id:
            raise CrossWorkspaceReference("Current Revision scope is inconsistent.")
        if current.id != expected_current_revision_id or scene.version != expected_scene_version:
            raise OptimisticConcurrencyConflict(
                current_revision_id=current.id,
                current_scene_version=scene.version,
            )

        try:
            operation = MutationOperation.objects.create(
                workspace=workspace,
                operation_type=MutationOperation.OperationType.SCENE_CONTENT_REVISED,
                source=MutationOperation.Source.OWNER,
                actor=actor,
                scene=scene,
            )
            revision = SceneRevision.objects.create(
                workspace=workspace,
                scene=scene,
                content=normalized_content,
                content_sha256=content_sha256(normalized_content),
                revision_number=current.revision_number + 1,
                content_format_version=CONTENT_FORMAT_VERSION,
                normalization_version=NORMALIZATION_VERSION,
                base_revision=current,
                restored_from=None,
                source=SceneRevision.Source.OWNER,
                actor=actor,
                mutation_operation=operation,
            )
            scene.current_revision = revision
            scene.version += 1
            scene.full_clean()
            scene.save(update_fields=("current_revision", "version", "updated_at"))
            from scenes.search_indexing import invalidate_and_enqueue_scene_search

            invalidate_and_enqueue_scene_search(scene, revision)
            from stories.workshop import record_writing_delta

            record_writing_delta(scene=scene, revision=revision, previous_content=current.content)
        except (IntegrityError, ValidationError) as exc:
            raise DomainIntegrityFailure(
                "Scene revision could not preserve domain integrity."
            ) from exc

    return SceneMutationResult(scene=scene, revision=revision, operation=operation)


def lock_authorized_workspace(actor: Account | AnonymousUser, workspace_id: uuid.UUID) -> Workspace:
    if not actor.is_authenticated or getattr(getattr(actor, "_state", None), "adding", False):
        raise NotAuthenticated("Authentication is required.")
    if not actor.is_active:
        raise SceneInaccessible("Workspace is unavailable.")

    try:
        get_authorized_workspace(actor, workspace_id)
    except Http404 as exc:
        raise SceneInaccessible("Workspace is unavailable.") from exc

    try:
        return cast(
            Workspace,
            Workspace.objects.select_for_update().get(
                id=workspace_id,
                is_active=True,
                grants__account=actor,
                grants__role=WorkspaceGrant.Role.OWNER,
                grants__state=WorkspaceGrant.State.ACTIVE,
            ),
        )
    except (Workspace.DoesNotExist, Workspace.MultipleObjectsReturned) as exc:
        raise SceneInaccessible("Workspace is unavailable.") from exc


__all__ = [
    "MAX_CONTENT_CHARACTERS",
    "MAX_TITLE_CHARACTERS",
    "SceneMutationIntent",
    "SceneMutationResult",
    "create_scene",
    "lock_authorized_workspace",
    "revise_scene_content",
    "validate_scene_ordering",
    "validate_scene_title",
]
