from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ai_assistance.adapters import (
    AdapterRequest,
    DeterministicFakeAdapter,
    OpenRouterAdapter,
    RetryableAdapterError,
    TerminalAdapterError,
)
from ai_assistance.context import assemble_context, snapshot_is_stale
from ai_assistance.models import (
    AICreativeConversion,
    AICreativeRequest,
    AICreativeSuggestion,
    VoiceProfile,
)
from ai_assistance.routing import route_for_task
from ai_assistance.tasks import get_task


def provider_available():
    if not settings.AI_ENABLED:
        return False
    if settings.AI_ADAPTER == "local_fake":
        return True
    return bool(
        settings.AI_ADAPTER == "openrouter" and settings.AI_OPENROUTER_API_KEY and settings.AI_MODEL
    )


def creative_adapter(model=""):
    if settings.AI_ADAPTER == "local_fake" and settings.DEBUG:
        return DeterministicFakeAdapter(), "deterministic-v1"
    if settings.AI_ADAPTER == "openrouter" and settings.AI_OPENROUTER_API_KEY:
        model = model.strip() or settings.AI_MODEL
        if not model:
            raise TerminalAdapterError("No provider model is configured.")
        return OpenRouterAdapter(
            api_key=settings.AI_OPENROUTER_API_KEY,
            model=model,
            timeout=settings.AI_TIMEOUT_SECONDS,
            maximum_tokens=settings.AI_MAX_OUTPUT_TOKENS,
        ), model
    raise TerminalAdapterError("No creative provider is configured.")


def run_creative_request(
    *, account, workspace, task_key, instruction, pack=None, chat_messages=(), model_override=""
):
    task = get_task(task_key)
    assembled = assemble_context(
        pack, task=task, instruction=instruction, chat_messages=chat_messages
    )
    route = route_for_task(task_key, model_override=model_override)
    primary_model = route.primary
    if settings.AI_ADAPTER == "local_fake" and settings.DEBUG:
        primary_model = "deterministic-v1"
    if not primary_model:
        raise TerminalAdapterError("No provider model is configured for this task.")
    request = AICreativeRequest.objects.create(
        workspace=workspace,
        requested_by=account,
        context_pack=pack,
        task_key=task_key,
        instruction=instruction,
        state="running",
        provider=settings.AI_ADAPTER,
        routing_category=route.category,
        model_identifier=primary_model,
        context_snapshot=assembled.snapshot,
        assembled_context=assembled.text,
        context_hash=assembled.context_hash,
        omission_report=assembled.omissions,
        provider_metadata={
            "routing_category": route.category,
            "configured_primary_model": primary_model,
        },
    )
    try:
        adapter_request = AdapterRequest(
            capability="creative_workspace",
            instruction=instruction,
            source_content=assembled.text,
            prompt_template=task_key,
            prompt_template_version="v1",
            configuration_version="creative-v1",
            maximum_output_characters=200_000,
        )
        attempted_models = []
        result = None
        candidates = (primary_model, *route.alternates)
        for index, model in enumerate(candidates):
            attempted_models.append(model)
            try:
                result = creative_adapter(model)[0].generate(adapter_request)
                break
            except RetryableAdapterError:
                if index == len(candidates) - 1:
                    raise
        if result is None:  # pragma: no cover - defensive, candidates always contain primary
            raise TerminalAdapterError("No provider model was attempted.")
        structured = parse_sections(result.proposed_text, task.output_sections)
    except Exception as exc:
        request.state = "failed"
        request.failure_classification = "provider_or_structure_failure"
        request.provider_metadata = {
            **request.provider_metadata,
            "attempted_models": attempted_models,
        }
        request.save(update_fields=("state", "failure_classification", "provider_metadata"))
        if isinstance(exc, TerminalAdapterError):
            raise
        raise TerminalAdapterError("Creative provider output could not be validated.") from exc
    request.state = "ready"
    request.completed_at = timezone.now()
    request.provider_metadata = {
        "provider": result.provider,
        "model": result.model,
        "routing_category": route.category,
        "configured_primary_model": primary_model,
        "attempted_models": attempted_models,
        "used_alternate": result.model != primary_model,
        "operation_identifier": result.operation_identifier,
        "input_units": result.input_units,
        "output_units": result.output_units,
    }
    request.model_identifier = result.model
    request.save(update_fields=("state", "completed_at", "model_identifier", "provider_metadata"))
    suggestion = AICreativeSuggestion.objects.create(
        workspace=workspace,
        request=request,
        original_output=result.proposed_text,
        reviewed_output=result.proposed_text,
        structured_output=structured,
    )
    return request, suggestion


def parse_sections(text, expected):
    sections = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current:
            sections[current].append(line)
    result = {key: "\n".join(value).strip() for key, value in sections.items()}
    if not result:
        raise ValueError("Structured output has no sections.")
    result["_expected_sections"] = list(expected)
    return result


def creative_suggestion_is_stale(suggestion):
    return snapshot_is_stale(suggestion.request.context_snapshot, suggestion.workspace)


@transaction.atomic
def review_creative_suggestion(suggestion, *, text, action, notes=""):
    suggestion = AICreativeSuggestion.objects.select_for_update().get(id=suggestion.id)
    if action not in ("save", "accept", "reject", "expire"):
        raise ValueError("Unsupported review action.")
    suggestion.reviewed_output = text
    suggestion.review_notes = notes
    suggestion.reviewed_at = timezone.now()
    suggestion.state = {
        "save": "editing",
        "accept": "accepted",
        "reject": "rejected",
        "expire": "expired",
    }[action]
    suggestion.save(update_fields=("reviewed_output", "review_notes", "reviewed_at", "state"))
    return suggestion


@transaction.atomic
def convert_suggestion(suggestion, *, target_type, title, content, action="create", target=None):
    from characters.models import Character
    from continuity.models import PlotThread
    from timeline.models import TimelineEvent
    from worldbuilding.models import Creature, WorldItem

    if suggestion.state not in ("accepted", "editing"):
        raise ValueError("Suggestion must be reviewed before conversion.")
    workspace = suggestion.workspace
    if target_type == "character":
        created = Character.objects.create(
            workspace=workspace, name=title, summary=content, notes=f"AI suggestion {suggestion.id}"
        )
    elif target_type == "creature":
        created = Creature.objects.create(
            workspace=workspace,
            name=title,
            creature_type="monster",
            appearance=content,
            encounter_notes=f"AI suggestion {suggestion.id}",
        )
    elif target_type == "item":
        created = WorldItem.objects.create(
            workspace=workspace,
            name=title,
            item_type="other",
            description=content,
            significance=f"AI suggestion {suggestion.id}",
        )
    elif target_type == "plot_thread":
        created = PlotThread.objects.create(
            workspace=workspace, title=title, short_summary=content, status="planned"
        )
    elif target_type == "timeline_event":
        if target is None or target.workspace_id != workspace.id:
            raise ValueError("A Workspace Timeline is required.")
        created = TimelineEvent.objects.create(
            workspace=workspace,
            timeline=target,
            work=target.work,
            title=title,
            description=content,
            status="planned",
            chronology_precision="unknown",
        )
    elif target_type == "voice_profile":
        created = VoiceProfile.objects.create(workspace=workspace, name=title, description=content)
    else:
        raise ValueError("Unsupported conversion target.")
    AICreativeConversion.objects.create(
        suggestion=suggestion,
        target_type=target_type,
        target_id=created.id,
        action=action,
        summary=title,
    )
    suggestion.state = "converted"
    suggestion.save(update_fields=("state",))
    return created
