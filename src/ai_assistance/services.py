import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import cast

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import Account
from ai_assistance.adapters import (
    AdapterRequest,
    AmbiguousAdapterError,
    DeterministicFakeAdapter,
    ProviderAdapter,
    RetryableAdapterError,
    TerminalAdapterError,
)
from ai_assistance.exceptions import AIRequestConflict, AIRequestUnavailable, StaleSuggestion
from ai_assistance.models import (
    AIContextManifest,
    AIRequest,
    AISuggestion,
    AISuggestionApplication,
    ProviderEffect,
)
from jobs.exceptions import AmbiguousJobOutcome, RetryableJobError, TerminalJobError
from jobs.models import Job, JobAttempt
from jobs.registry import JobContext
from jobs.services import enqueue_job, request_cancellation
from scenes.content import MAX_CONTENT_CHARACTERS, content_sha256, normalize_scene_content
from scenes.exceptions import InvalidSceneContent
from scenes.models import Scene
from scenes.save_requests import SaveRequestOutcome, save_scene_content
from workspaces.models import WorkspaceGrant
from workspaces.services import get_authorized_workspace

CAPABILITY = "scene_revision_suggestion"
CONFIGURATION_VERSION = "ai-scene-v1"
MAX_INSTRUCTION_CHARACTERS = 1000


@dataclass(frozen=True, slots=True)
class RequestResult:
    request: AIRequest
    replayed: bool


def request_suggestion(
    *, account: Account, scene_id: uuid.UUID, instruction: str, idempotency_key: str
) -> RequestResult:
    if not isinstance(instruction, str) or not instruction.strip() or "\x00" in instruction:
        raise AIRequestUnavailable("Instruction is invalid.")
    instruction = instruction.strip()
    if len(instruction) > MAX_INSTRUCTION_CHARACTERS:
        raise AIRequestUnavailable("Instruction exceeds the supported limit.")
    if not settings.AI_ENABLED:
        raise AIRequestUnavailable("AI assistance is disabled.")
    workspace = get_authorized_workspace(account, _scene_workspace_id(scene_id))
    with transaction.atomic():
        try:
            scene = cast(
                Scene,
                Scene.objects.select_for_update(of=("self",))
                .select_related("current_revision")
                .get(id=scene_id, workspace=workspace, lifecycle=Scene.Lifecycle.ACTIVE),
            )
        except Scene.DoesNotExist as exc:
            raise AIRequestUnavailable("Scene is unavailable.") from exc
        source = scene.current_revision
        if source is None:
            raise AIRequestUnavailable("Scene has no current Revision.")
        instruction_hash = hashlib.sha256(instruction.encode()).hexdigest()
        fingerprint = _request_fingerprint(
            workspace_id=workspace.id,
            account_id=account.id,
            scene=scene,
            instruction_hash=instruction_hash,
        )
        existing = (
            AIRequest.objects.select_for_update()
            .filter(workspace=workspace, requested_by=account, idempotency_key=idempotency_key)
            .first()
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise AIRequestConflict("AI request identifier was reused.")
            return RequestResult(existing, True)
        request = AIRequest.objects.create(
            workspace=workspace,
            requested_by=account,
            scene=scene,
            source_revision=source,
            source_scene_version=scene.version,
            source_content_hash=source.content_sha256,
            instruction=instruction,
            instruction_hash=instruction_hash,
            request_fingerprint=fingerprint,
            idempotency_key=idempotency_key,
            provider=settings.AI_ADAPTER,
        )
        AIContextManifest.objects.create(
            request=request,
            workspace=workspace,
            scene=scene,
            source_revision=source,
            source_scene_version=scene.version,
            source_content_hash=source.content_sha256,
            capability=CAPABILITY,
            prompt_template=request.prompt_template,
            prompt_template_version=request.prompt_template_version,
            configuration_version=CONFIGURATION_VERSION,
        )
        enqueue = enqueue_job(
            workspace=workspace,
            caller="web",
            caller_reference=f"account-{account.id.hex}",
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            job_type="generate_ai_scene_suggestion",
            target_category="ai_request",
            target_id=request.id,
            expected_revision_id=source.id,
            expected_scene_version=scene.version,
            projection_version=CONFIGURATION_VERSION,
            effect_class="external_ambiguous",
        )
        AIRequest.objects.filter(id=request.id).update(job=enqueue.job)
        request.refresh_from_db()
        return RequestResult(request, False)


def _scene_workspace_id(scene_id: uuid.UUID) -> uuid.UUID:
    value = Scene.objects.filter(id=scene_id).values_list("workspace_id", flat=True).first()
    if value is None:
        raise AIRequestUnavailable("Scene is unavailable.")
    return cast(uuid.UUID, value)


def _request_fingerprint(
    *, workspace_id: uuid.UUID, account_id: uuid.UUID, scene: Scene, instruction_hash: str
) -> str:
    source = scene.current_revision
    if source is None:
        raise AIRequestUnavailable("Scene has no current Revision.")
    value = {
        "account": str(account_id),
        "capability": CAPABILITY,
        "configuration": CONFIGURATION_VERSION,
        "instruction_hash": instruction_hash,
        "scene": str(scene.id),
        "scene_version": scene.version,
        "source_hash": source.content_sha256,
        "source_revision": str(source.id),
        "template": "scene-review:v1",
        "workspace": str(workspace_id),
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def get_configured_adapter() -> ProviderAdapter:
    if settings.AI_ADAPTER == "local_fake" and settings.DEBUG:
        return DeterministicFakeAdapter()
    raise TerminalAdapterError("No production AI provider adapter is configured.")


def generate_suggestion(context: JobContext) -> None:
    job = cast(Job, Job.execution_objects.get(id=uuid.UUID(context.job_id)))
    request = cast(
        AIRequest,
        AIRequest.objects.select_related("scene", "source_revision").get(id=job.target_id),
    )
    if request.state == AIRequest.State.COMPLETED and hasattr(request, "suggestion"):
        return
    if context.cancellation_requested():
        AIRequest.objects.filter(id=request.id).update(
            state=AIRequest.State.CANCELLED, cancelled_at=timezone.now()
        )
        raise TerminalJobError("AI request was cancelled.")
    if not _request_authorized_and_current(request):
        AIRequest.objects.filter(id=request.id).update(
            state=AIRequest.State.EXPIRED,
            failure_classification="stale_source",
            expired_at=timezone.now(),
        )
        return
    attempt = JobAttempt.execution_objects.filter(job=job, attempt_number=job.attempt_count).first()
    effect = ProviderEffect.objects.create(
        request=request,
        job_attempt=attempt,
        provider=request.provider,
        outcome=ProviderEffect.Outcome.INTENDED,
        requested_at=timezone.now(),
    )
    AIRequest.objects.filter(id=request.id).update(
        state=AIRequest.State.RUNNING, started_at=timezone.now()
    )
    adapter_request = AdapterRequest(
        capability=request.capability,
        instruction=request.instruction,
        source_content=request.source_revision.content,
        prompt_template=request.prompt_template,
        prompt_template_version=request.prompt_template_version,
        configuration_version=request.configuration_version,
        maximum_output_characters=request.maximum_output_characters,
    )
    try:
        result = get_configured_adapter().generate(adapter_request)
        if context.cancellation_requested():
            ProviderEffect.objects.filter(id=effect.id).update(
                outcome=ProviderEffect.Outcome.CANCELLED, acknowledged_at=timezone.now()
            )
            AIRequest.objects.filter(id=request.id).update(
                state=AIRequest.State.CANCELLED, cancelled_at=timezone.now()
            )
            raise TerminalJobError("AI request was cancelled.")
        output = normalize_scene_content(result.proposed_text)
        if len(output) > MAX_CONTENT_CHARACTERS:
            raise TerminalAdapterError("Provider output exceeds the supported limit.")
    except RetryableAdapterError as exc:
        ProviderEffect.objects.filter(id=effect.id).update(
            outcome=ProviderEffect.Outcome.KNOWN_FAILURE, acknowledged_at=timezone.now()
        )
        raise RetryableJobError("AI provider is temporarily unavailable.") from exc
    except AmbiguousAdapterError as exc:
        ProviderEffect.objects.filter(id=effect.id).update(
            outcome=ProviderEffect.Outcome.AMBIGUOUS,
            ambiguity_classification="unknown_outcome",
            acknowledged_at=timezone.now(),
        )
        AIRequest.objects.filter(id=request.id).update(
            state=AIRequest.State.QUARANTINED,
            failure_classification="ambiguous",
            quarantined_at=timezone.now(),
        )
        raise AmbiguousJobOutcome("AI provider outcome is ambiguous.") from exc
    except (TerminalAdapterError, InvalidSceneContent) as exc:
        ProviderEffect.objects.filter(id=effect.id).update(
            outcome=ProviderEffect.Outcome.KNOWN_FAILURE, acknowledged_at=timezone.now()
        )
        AIRequest.objects.filter(id=request.id).update(
            state=AIRequest.State.FAILED,
            failure_classification="provider_failure",
            failed_at=timezone.now(),
        )
        raise TerminalJobError("AI provider request failed terminally.") from exc
    with transaction.atomic():
        request = cast(AIRequest, AIRequest.objects.select_for_update().get(id=request.id))
        suggestion, _ = AISuggestion.objects.get_or_create(
            request=request,
            defaults={
                "workspace": request.workspace,
                "scene": request.scene,
                "source_revision": request.source_revision,
                "source_scene_version": request.source_scene_version,
                "source_content_hash": request.source_content_hash,
                "original_output": output,
                "review_text": output,
                "output_hash": content_sha256(output),
                "state": AISuggestion.State.READY,
                "provider": result.provider,
                "model_classification": result.model,
                "prompt_template": request.prompt_template,
                "prompt_template_version": request.prompt_template_version,
                "provider_operation_identifier": result.operation_identifier,
                "input_units": result.input_units,
                "output_units": result.output_units,
            },
        )
        del suggestion
        ProviderEffect.objects.filter(id=effect.id).update(
            outcome=ProviderEffect.Outcome.KNOWN_SUCCESS,
            operation_identifier=result.operation_identifier,
            acknowledged_at=timezone.now(),
        )
        AIRequest.objects.filter(id=request.id).update(
            state=AIRequest.State.COMPLETED, completed_at=timezone.now()
        )


def _request_authorized_and_current(request: AIRequest) -> bool:
    grant = WorkspaceGrant.objects.filter(
        workspace_id=request.workspace_id,
        account_id=request.requested_by_id,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    ).exists()
    scene = (
        Scene.objects.select_related("current_revision")
        .filter(
            id=request.scene_id, workspace_id=request.workspace_id, lifecycle=Scene.Lifecycle.ACTIVE
        )
        .first()
    )
    return bool(
        grant
        and scene is not None
        and scene.current_revision_id == request.source_revision_id
        and scene.version == request.source_scene_version
        and scene.current_revision is not None
        and scene.current_revision.content_sha256 == request.source_content_hash
    )


def suggestion_is_stale(suggestion: AISuggestion) -> bool:
    scene = Scene.objects.select_related("current_revision").get(id=suggestion.scene_id)
    return bool(
        scene.current_revision_id != suggestion.source_revision_id
        or scene.version != suggestion.source_scene_version
        or scene.current_revision is None
        or scene.current_revision.content_sha256 != suggestion.source_content_hash
        or scene.lifecycle != Scene.Lifecycle.ACTIVE
    )


def apply_suggestion(
    *, account: Account, suggestion_id: uuid.UUID, review_text: str, idempotency_key: str
) -> AISuggestion:
    normalized = normalize_scene_content(review_text)
    with transaction.atomic():
        suggestion = cast(
            AISuggestion,
            AISuggestion.objects.select_for_update()
            .select_related("scene", "request")
            .get(id=suggestion_id),
        )
        get_authorized_workspace(account, suggestion.workspace_id)
        if suggestion.state == AISuggestion.State.APPLIED:
            return suggestion
        if suggestion.state != AISuggestion.State.READY:
            raise AIRequestUnavailable("Suggestion is not applicable.")
        if suggestion_is_stale(suggestion):
            raise StaleSuggestion("Suggestion source is stale.")
        result = save_scene_content(
            actor=account,
            workspace_id=suggestion.workspace_id,
            scene_id=suggestion.scene_id,
            expected_current_revision_id=suggestion.source_revision_id,
            expected_scene_version=suggestion.source_scene_version,
            proposed_content=normalized,
            idempotency_key=idempotency_key,
            save_intent="explicit_save",
        )
        if result.outcome is not SaveRequestOutcome.SUCCEEDED:
            raise StaleSuggestion("Suggestion application conflicted.")
        AISuggestionApplication.objects.get_or_create(
            suggestion=suggestion,
            defaults={
                "revision": result.revision,
                "mutation_operation": result.revision.mutation_operation,
                "applied_text_hash": content_sha256(normalized),
                "human_edited": normalized != suggestion.original_output,
            },
        )
        AISuggestion.objects.filter(id=suggestion.id).update(
            review_text=normalized,
            state=AISuggestion.State.APPLIED,
            reviewed_at=timezone.now(),
            applied_at=timezone.now(),
            reviewed_by=account,
            applied_by=account,
            resulting_revision=result.revision,
            resulting_scene_version=result.scene_version,
            disposition_classification=(
                "applied_edited" if normalized != suggestion.original_output else "applied_full"
            ),
        )
        return cast(AISuggestion, AISuggestion.objects.get(id=suggestion.id))


def reject_suggestion(*, account: Account, suggestion_id: uuid.UUID) -> AISuggestion:
    return _dispose(account, suggestion_id, "rejected")


def expire_suggestion(*, account: Account, suggestion_id: uuid.UUID) -> AISuggestion:
    return _dispose(account, suggestion_id, "expired")


def _dispose(account: Account, suggestion_id: uuid.UUID, state: str) -> AISuggestion:
    with transaction.atomic():
        suggestion = cast(
            AISuggestion, AISuggestion.objects.select_for_update().get(id=suggestion_id)
        )
        get_authorized_workspace(account, suggestion.workspace_id)
        if suggestion.state == state:
            return suggestion
        if suggestion.state != AISuggestion.State.READY:
            raise AIRequestUnavailable("Suggestion disposition is unavailable.")
        now = timezone.now()
        updates = {"state": state, "reviewed_by": account, "reviewed_at": now}
        updates["rejected_at" if state == "rejected" else "expired_at"] = now
        AISuggestion.objects.filter(id=suggestion.id).update(**updates)
        return cast(AISuggestion, AISuggestion.objects.get(id=suggestion.id))


def quarantine_unfinished_ai_requests() -> int:
    return cast(
        int,
        AIRequest.objects.filter(
            state__in=(AIRequest.State.QUEUED, AIRequest.State.RUNNING)
        ).update(
            state=AIRequest.State.QUARANTINED,
            failure_classification="ambiguous",
            quarantined_at=timezone.now(),
        ),
    )


def cancel_ai_request(*, account: Account, request_id: uuid.UUID) -> AIRequest:
    with transaction.atomic():
        request = cast(AIRequest, AIRequest.objects.select_for_update().get(id=request_id))
        get_authorized_workspace(account, request.workspace_id)
        if request.state == AIRequest.State.CANCELLED:
            return request
        if request.state not in (AIRequest.State.QUEUED, AIRequest.State.RUNNING):
            raise AIRequestUnavailable("AI Request cannot be cancelled.")
        if request.job_id is not None:
            request_cancellation(request.job_id)
        AIRequest.objects.filter(id=request.id).update(
            state=AIRequest.State.CANCELLED, cancelled_at=timezone.now()
        )
        return cast(AIRequest, AIRequest.objects.get(id=request.id))
