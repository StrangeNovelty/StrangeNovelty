import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Account
from scenes.content import content_sha256, normalize_scene_content
from scenes.exceptions import OptimisticConcurrencyConflict, SceneInaccessible
from scenes.models import Scene, SceneRevision, SceneSaveRequest
from scenes.services import (
    SceneMutationIntent,
    lock_authorized_workspace,
    revise_scene_content,
)
from security_events.services import (
    SecurityEventSpec,
    record_security_event,
    validated_correlation_id,
)
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")


class SaveRequestOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    CONFLICTED = "conflicted"
    IDEMPOTENCY_CONFLICTED = "idempotency_conflicted"


class IdempotencyKeyConflict(Exception):
    """The same scoped key was reused for different semantic input."""


@dataclass(frozen=True, slots=True)
class SceneSaveResult:
    outcome: SaveRequestOutcome
    scene: Scene
    revision: SceneRevision
    scene_version: int
    replayed: bool


def scene_save_fingerprint(
    *,
    scene_id: uuid.UUID,
    expected_current_revision_id: uuid.UUID,
    expected_scene_version: int,
    normalized_content_hash: str,
    save_intent: str,
) -> str:
    payload = {
        "content_sha256": normalized_content_hash,
        "expected_current_revision_id": str(expected_current_revision_id),
        "expected_scene_version": expected_scene_version,
        "save_intent": save_intent,
        "scene_id": str(scene_id),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def save_scene_content(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    scene_id: uuid.UUID,
    expected_current_revision_id: uuid.UUID,
    expected_scene_version: int,
    proposed_content: str,
    idempotency_key: str,
    save_intent: str,
    correlation_id: str | None = None,
) -> SceneSaveResult:
    if save_intent != "explicit_save":
        raise ValueError("Unsupported save intent.")
    if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
        raise ValueError("Invalid idempotency key.")
    normalized = normalize_scene_content(proposed_content)
    fingerprint = scene_save_fingerprint(
        scene_id=scene_id,
        expected_current_revision_id=expected_current_revision_id,
        expected_scene_version=expected_scene_version,
        normalized_content_hash=content_sha256(normalized),
        save_intent=save_intent,
    )

    safe_correlation_id = validated_correlation_id(correlation_id)
    with transaction.atomic():
        workspace = lock_authorized_workspace(actor, workspace_id)
        account = cast(Account, actor)
        try:
            scene = cast(
                Scene,
                Scene.objects.select_for_update()
                .select_related("current_revision")
                .get(id=scene_id, workspace=workspace),
            )
        except Scene.DoesNotExist as exc:
            raise SceneInaccessible("Scene is unavailable.") from exc

        request_record = _reserve_or_lock_request(
            workspace_id=workspace.id,
            account_id=account.id,
            scene_id=scene.id,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if request_record.request_fingerprint != fingerprint:
            current = scene.current_revision
            if current is None:
                raise RuntimeError("Scene has no current Revision.")
            record_security_event(
                SecurityEventSpec(
                    event_type=SecurityEventType.SCENE_SAVE_KEY_CONFLICT,
                    outcome=SecurityOutcome.CONFLICTED,
                    actor=account,
                    workspace=workspace,
                    target_category=SecurityTargetCategory.SCENE,
                    target_id=scene.id,
                    correlation_id=safe_correlation_id,
                    service_role=SecurityServiceRole.WEB,
                    reason=SecurityReason.IDEMPOTENCY_KEY_REUSE,
                )
            )
            return SceneSaveResult(
                outcome=SaveRequestOutcome.IDEMPOTENCY_CONFLICTED,
                scene=scene,
                revision=current,
                scene_version=scene.version,
                replayed=False,
            )
        replay = _replay_result(request_record, scene)
        if replay is not None:
            return replay

        try:
            mutation = revise_scene_content(
                actor=actor,
                workspace_id=workspace.id,
                scene_id=scene.id,
                expected_current_revision_id=expected_current_revision_id,
                expected_scene_version=expected_scene_version,
                proposed_content=normalized,
                intent=SceneMutationIntent.CONTENT_REVISION,
            )
        except OptimisticConcurrencyConflict:
            current = cast(SceneRevision, scene.current_revision)
            request_record.state = SceneSaveRequest.State.CONFLICTED
            request_record.failure_classification = (
                SceneSaveRequest.FailureClassification.OPTIMISTIC_CONCURRENCY
            )
            request_record.completed_at = timezone.now()
            request_record.save(
                update_fields=("state", "failure_classification", "completed_at", "updated_at")
            )
            record_security_event(
                SecurityEventSpec(
                    event_type=SecurityEventType.SCENE_SAVE_CONFLICT,
                    outcome=SecurityOutcome.CONFLICTED,
                    actor=account,
                    workspace=workspace,
                    target_category=SecurityTargetCategory.SCENE,
                    target_id=scene.id,
                    correlation_id=safe_correlation_id,
                    service_role=SecurityServiceRole.WEB,
                    reason=SecurityReason.OPTIMISTIC_CONCURRENCY,
                )
            )
            result = SceneSaveResult(
                outcome=SaveRequestOutcome.CONFLICTED,
                scene=scene,
                revision=current,
                scene_version=scene.version,
                replayed=False,
            )
        else:
            request_record.state = SceneSaveRequest.State.SUCCEEDED
            request_record.result_revision = mutation.revision
            request_record.result_scene_version = mutation.scene.version
            request_record.completed_at = timezone.now()
            request_record.save(
                update_fields=(
                    "state",
                    "result_revision",
                    "result_scene_version",
                    "completed_at",
                    "updated_at",
                )
            )
            result = SceneSaveResult(
                outcome=SaveRequestOutcome.SUCCEEDED,
                scene=mutation.scene,
                revision=mutation.revision,
                scene_version=mutation.scene.version,
                replayed=False,
            )

    return result


def _reserve_or_lock_request(
    *,
    workspace_id: uuid.UUID,
    account_id: uuid.UUID,
    scene_id: uuid.UUID,
    idempotency_key: str,
    fingerprint: str,
) -> SceneSaveRequest:
    lookup = {
        "workspace_id": workspace_id,
        "account_id": account_id,
        "scene_id": scene_id,
        "idempotency_key": idempotency_key,
    }
    try:
        return cast(SceneSaveRequest, SceneSaveRequest.objects.select_for_update().get(**lookup))
    except SceneSaveRequest.DoesNotExist:
        try:
            with transaction.atomic():
                SceneSaveRequest.objects.create(request_fingerprint=fingerprint, **lookup)
        except IntegrityError:
            pass
        return cast(SceneSaveRequest, SceneSaveRequest.objects.select_for_update().get(**lookup))


def _replay_result(request_record: SceneSaveRequest, scene: Scene) -> SceneSaveResult | None:
    if request_record.state == SceneSaveRequest.State.SUCCEEDED:
        revision = request_record.result_revision
        version = request_record.result_scene_version
        if revision is None or version is None:
            raise RuntimeError("Successful save request has no result.")
        return SceneSaveResult(
            outcome=SaveRequestOutcome.SUCCEEDED,
            scene=scene,
            revision=revision,
            scene_version=version,
            replayed=True,
        )
    if request_record.state == SceneSaveRequest.State.CONFLICTED:
        current = scene.current_revision
        if current is None:
            raise RuntimeError("Scene has no current Revision.")
        return SceneSaveResult(
            outcome=SaveRequestOutcome.CONFLICTED,
            scene=scene,
            revision=current,
            scene_version=scene.version,
            replayed=True,
        )
    if request_record.state == SceneSaveRequest.State.PENDING:
        return None
    raise IdempotencyKeyConflict
