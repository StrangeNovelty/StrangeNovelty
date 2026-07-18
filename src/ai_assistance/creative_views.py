import uuid

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from ai_assistance.adapters import TerminalAdapterError
from ai_assistance.brainstorm import MODES as BRAINSTORM_MODES
from ai_assistance.brainstorm import instruction_for
from ai_assistance.context import assemble_context
from ai_assistance.creative_forms import (
    BrainstormSessionForm,
    ChatMessageForm,
    ChatSessionForm,
    ContextPackForm,
    ConversionForm,
    CreativeRequestForm,
    CreativeReviewForm,
    VoiceProfileForm,
)
from ai_assistance.creative_services import (
    convert_suggestion,
    creative_suggestion_is_stale,
    provider_available,
    review_creative_suggestion,
    run_creative_request,
)
from ai_assistance.models import (
    AIChatMessage,
    AIChatSession,
    AIContextCharacterLink,
    AIContextDrawLink,
    AIContextLocationLink,
    AIContextPack,
    AICreativeSuggestion,
    BrainstormSession,
    VoiceProfile,
)
from ai_assistance.tasks import CATEGORIES, TASKS, get_task
from workspaces.services import resolve_owner_workspace


def workspace_for(request):
    return resolve_owner_workspace(request.user)


@never_cache
@login_required
def brainstorm_list(request):
    workspace = workspace_for(request)
    sessions = workspace.brainstorm_sessions.select_related(
        "work", "chapter", "draw", "latest_suggestion"
    )
    return render(
        request,
        "ai_assistance/brainstorm_list.html",
        {"workspace": workspace, "sessions": sessions, "modes": BRAINSTORM_MODES.values()},
    )


@login_required
@require_POST
@transaction.atomic
def brainstorm_create(request):
    workspace = workspace_for(request)
    mode = request.POST.get("mode", "plot")
    if mode not in BRAINSTORM_MODES:
        raise Http404
    pack = AIContextPack.objects.create(
        workspace=workspace,
        name=f"Brainstorm {uuid.uuid4()}",
        description="Context owned by a persistent Story Engine Brainstorm session.",
        status="active",
    )
    session = BrainstormSession.objects.create(
        workspace=workspace,
        title=BRAINSTORM_MODES[mode].title,
        mode=mode,
        context_pack=pack,
    )
    return redirect("brainstorm-detail", session.id)


def _save_brainstorm_form(form, session):
    session = form.save(commit=False)
    session.mode_settings = {
        "threat_level": form.cleaned_data.get("threat_level", ""),
        "discipline": form.cleaned_data.get("discipline", ""),
    }
    session.full_clean()
    session.save()
    pack = session.context_pack
    pack.name = f"Brainstorm · {session.title} · {str(session.id)[:8]}"[:240]
    pack.work = session.work
    pack.chapter = session.chapter
    pack.exclusions = session.exclusions
    pack.author_instructions = session.focus
    pack.save()
    pack.aicontextcharacterlink_set.all().delete()
    pack.aicontextlocationlink_set.all().delete()
    pack.aicontextdrawlink_set.all().delete()
    for order, character in enumerate(form.cleaned_data["characters"]):
        AIContextCharacterLink.objects.create(
            pack=pack, character=character, role="selected cast", priority=10, order=order
        )
    for order, location in enumerate(form.cleaned_data["locations"]):
        AIContextLocationLink.objects.create(
            pack=pack, location=location, role="immediate setting", priority=20, order=order
        )
    if session.draw:
        AIContextDrawLink.objects.create(
            pack=pack, draw=session.draw, role="Story Engine Cards", priority=5
        )
    return session


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def brainstorm_detail(request, session_id):
    workspace = workspace_for(request)
    session = get_object_or_404(
        BrainstormSession.objects.select_related(
            "context_pack", "work", "chapter", "draw", "latest_suggestion"
        ),
        id=session_id,
        workspace=workspace,
    )
    form = BrainstormSessionForm(request.POST or None, instance=session, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            session = _save_brainstorm_form(form, session)
            if request.POST.get("action") == "generate":
                try:
                    _, suggestion = run_creative_request(
                        account=request.user,
                        workspace=workspace,
                        task_key=BRAINSTORM_MODES[session.mode].task_key,
                        instruction=instruction_for(session),
                        pack=session.context_pack,
                    )
                except TerminalAdapterError:
                    form.add_error(None, "The configured provider returned no usable result.")
                else:
                    session.latest_suggestion = suggestion
                    session.save(update_fields=("latest_suggestion", "updated_at"))
                    return redirect("ai-creative-review", suggestion.id)
            else:
                return redirect("brainstorm-detail", session.id)
    mode = BRAINSTORM_MODES[session.mode]
    preview = assemble_context(
        session.context_pack, task=get_task(mode.task_key), instruction=instruction_for(session)
    )
    return render(
        request,
        "ai_assistance/brainstorm_detail.html",
        {
            "session": session,
            "form": form,
            "mode": mode,
            "modes": BRAINSTORM_MODES.values(),
            "preview": preview,
            "provider_available": provider_available(),
        },
    )


CONTEXT_LINKS = {
    "volume": ("stories", "Volume", "AIContextVolumeLink", "volume", "workspace"),
    "arc": ("stories", "Arc", "AIContextArcLink", "arc", "workspace"),
    "scene": ("scenes", "Scene", "AIContextSceneLink", "scene", "workspace"),
    "character": ("characters", "Character", "AIContextCharacterLink", "character", "workspace"),
    "group": ("characters", "CharacterGroup", "AIContextGroupLink", "group", "workspace"),
    "ability": ("characters", "Ability", "AIContextAbilityLink", "ability", "workspace"),
    "location": ("worldbuilding", "Location", "AIContextLocationLink", "location", "workspace"),
    "region": ("worldbuilding", "Region", "AIContextRegionLink", "region", "workspace"),
    "codex": ("worldbuilding", "CodexEntry", "AIContextCodexLink", "codex", "workspace"),
    "item": ("worldbuilding", "WorldItem", "AIContextItemLink", "item", "workspace"),
    "creature": ("worldbuilding", "Creature", "AIContextCreatureLink", "creature", "workspace"),
    "thread": ("continuity", "PlotThread", "AIContextThreadLink", "thread", "workspace"),
    "secret": ("continuity", "Secret", "AIContextSecretLink", "secret", "workspace"),
    "clue": ("continuity", "ThreadClue", "AIContextClueLink", "clue", "thread__workspace"),
    "reveal": (
        "continuity",
        "ThreadReveal",
        "AIContextRevealLink",
        "reveal",
        "thread__workspace",
    ),
    "reader_knowledge": (
        "continuity",
        "ReaderKnowledgeRecord",
        "AIContextReaderKnowledgeLink",
        "reader_knowledge",
        "workspace",
    ),
    "character_knowledge": (
        "continuity",
        "CharacterKnowledgeRecord",
        "AIContextCharacterKnowledgeLink",
        "character_knowledge",
        "workspace",
    ),
    "timeline": ("timeline", "Timeline", "AIContextTimelineLink", "timeline", "workspace"),
    "timeline_event": (
        "timeline",
        "TimelineEvent",
        "AIContextTimelineEventLink",
        "timeline_event",
        "workspace",
    ),
    "draw": ("decks", "SavedDraw", "AIContextDrawLink", "draw", "workspace"),
    "interpretation": (
        "decks",
        "DrawInterpretation",
        "AIContextInterpretationLink",
        "interpretation",
        "draw__workspace",
    ),
    "card": ("decks", "DeckCard", "AIContextCardLink", "card", "deck__workspace"),
    "research_source": (
        "library",
        "ResearchSource",
        "AIContextResearchSourceLink",
        "research_source",
        "workspace",
    ),
    "research_note": (
        "library",
        "ResearchNote",
        "AIContextResearchNoteLink",
        "research_note",
        "workspace",
    ),
    "artwork": ("library", "ArtworkAsset", "AIContextArtworkLink", "artwork", "workspace"),
    "collection": (
        "library",
        "LibraryCollection",
        "AIContextCollectionLink",
        "collection",
        "workspace",
    ),
    "manuscript": (
        "publishing",
        "ManuscriptProject",
        "AIContextManuscriptLink",
        "manuscript",
        "workspace",
    ),
}


@never_cache
@login_required
def ai_workspace(request):
    workspace = workspace_for(request)
    grouped = {
        category: [task for task in TASKS.values() if task.category == category]
        for category in CATEGORIES
    }
    return render(
        request,
        "ai_assistance/workspace.html",
        {
            "workspace": workspace,
            "grouped_tasks": grouped,
            "provider_available": provider_available(),
            "provider_name": settings.AI_ADAPTER,
            "packs": workspace.ai_context_packs.exclude(status="archived")[:8],
            "chats": workspace.ai_chat_sessions.filter(status="active")[:5],
            "requests": workspace.ai_creative_requests.all()[:10],
            "awaiting_count": workspace.ai_creative_suggestions.filter(
                state__in=("ready", "editing")
            ).count(),
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def context_pack_create(request):
    workspace = workspace_for(request)
    form = ContextPackForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        pack = form.save(commit=False)
        pack.workspace = workspace
        pack.full_clean()
        pack.save()
        return redirect("ai-context-pack-detail", pack.id)
    return render(
        request, "ai_assistance/generic_form.html", {"form": form, "heading": "Create Context Pack"}
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def context_pack_detail(request, pack_id):
    workspace = workspace_for(request)
    pack = get_object_or_404(AIContextPack, id=pack_id, workspace=workspace)
    form = ContextPackForm(request.POST or None, instance=pack, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("ai-context-pack-detail", pack.id)
    options = {}
    for kind, (app_label, model_name, _, _, scope) in CONTEXT_LINKS.items():
        options[kind] = apps.get_model(app_label, model_name).objects.filter(**{scope: workspace})[
            :200
        ]
    preview = assemble_context(pack, task=get_task("story_chat"), instruction="Context preview")
    return render(
        request,
        "ai_assistance/context_pack.html",
        {"pack": pack, "form": form, "link_options": options, "preview": preview},
    )


@login_required
@require_POST
def context_pack_transition(request, pack_id):
    workspace = workspace_for(request)
    pack = get_object_or_404(AIContextPack, id=pack_id, workspace=workspace)
    status = request.POST.get("status")
    if status not in dict(AIContextPack.STATUSES):
        raise Http404
    pack.status = status
    pack.save(update_fields=("status", "updated_at"))
    return redirect("ai-context-pack-detail", pack.id)


@login_required
@require_POST
def context_pack_link(request, pack_id, kind):
    workspace = workspace_for(request)
    pack = get_object_or_404(AIContextPack, id=pack_id, workspace=workspace)
    if kind not in CONTEXT_LINKS:
        raise Http404
    app_label, model_name, link_name, field, scope = CONTEXT_LINKS[kind]
    record = get_object_or_404(
        apps.get_model(app_label, model_name),
        id=request.POST.get("record_id"),
        **{scope: workspace},
    )
    link = apps.get_model("ai_assistance", link_name)(
        pack=pack,
        role=request.POST.get("role", ""),
        priority=request.POST.get("priority", 50),
        **{field: record},
    )
    link.full_clean()
    link.save()
    return redirect("ai-context-pack-detail", pack.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def creative_request(request):
    workspace = workspace_for(request)
    initial_task = request.GET.get("task")
    form = CreativeRequestForm(request.POST or None, workspace=workspace, initial_task=initial_task)
    preview = None
    if request.method == "POST" and form.is_valid():
        task = get_task(form.cleaned_data["task_key"])
        preview = assemble_context(
            form.cleaned_data["context_pack"],
            task=task,
            instruction=form.cleaned_data["instruction"],
        )
        if request.POST.get("action") == "submit":
            try:
                _, suggestion = run_creative_request(
                    account=request.user,
                    workspace=workspace,
                    task_key=task.key,
                    instruction=form.cleaned_data["instruction"],
                    pack=form.cleaned_data["context_pack"],
                    model_override=form.cleaned_data["model_override"],
                )
            except TerminalAdapterError:
                form.add_error(
                    None, "The configured provider is unavailable or returned unusable output."
                )
            else:
                return redirect("ai-creative-review", suggestion.id)
    return render(
        request,
        "ai_assistance/creative_request.html",
        {"form": form, "preview": preview, "provider_available": provider_available()},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def creative_review(request, suggestion_id):
    workspace = workspace_for(request)
    suggestion = get_object_or_404(
        AICreativeSuggestion.objects.select_related("request"),
        id=suggestion_id,
        workspace=workspace,
    )
    form = CreativeReviewForm(
        request.POST or None,
        initial={
            "reviewed_output": suggestion.reviewed_output,
            "review_notes": suggestion.review_notes,
        },
    )
    if request.method == "POST" and form.is_valid():
        review_creative_suggestion(
            suggestion,
            text=form.cleaned_data["reviewed_output"],
            notes=form.cleaned_data["review_notes"],
            action=request.POST.get("action", "save"),
        )
        return redirect("ai-creative-review", suggestion.id)
    return render(
        request,
        "ai_assistance/creative_review.html",
        {
            "suggestion": suggestion,
            "form": form,
            "stale": creative_suggestion_is_stale(suggestion),
            "conversion_form": ConversionForm(
                workspace=workspace,
                initial={
                    "title": get_task(suggestion.request.task_key).title,
                    "content": suggestion.reviewed_output,
                },
            ),
        },
    )


@login_required
@require_POST
def creative_convert(request, suggestion_id):
    workspace = workspace_for(request)
    suggestion = get_object_or_404(AICreativeSuggestion, id=suggestion_id, workspace=workspace)
    form = ConversionForm(request.POST, workspace=workspace)
    if not form.is_valid():
        raise Http404("Conversion preview is invalid.")
    target_type = form.cleaned_data["target_type"]
    selected_target = (
        form.cleaned_data["chapter"]
        if target_type.startswith("chapter_")
        else form.cleaned_data["timeline"]
    )
    created = convert_suggestion(
        suggestion,
        target_type=target_type,
        title=form.cleaned_data["title"],
        content=form.cleaned_data["content"],
        action=form.cleaned_data["action"],
        target=selected_target,
    )
    if target_type == "character":
        return redirect("character-detail", created.id)
    if target_type in ("location", "region", "creature", "item"):
        kind = {"item": "items"}.get(target_type, f"{target_type}s")
        return redirect("world-record-detail", kind=kind, record_id=created.id)
    if target_type == "plot_thread":
        return redirect("continuity-thread-detail", created.id)
    if target_type == "timeline_event":
        return redirect("timeline-event-detail", created.id)
    if target_type.startswith("chapter_"):
        return redirect("chapter-detail", created.work_id, created.id)
    if target_type == "voice_profile":
        return redirect("ai-voice-profile", created.id)
    return redirect("ai-creative-review", suggestion.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chat_create(request):
    workspace = workspace_for(request)
    form = ChatSessionForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        chat = form.save(commit=False)
        chat.workspace = workspace
        chat.save()
        return redirect("ai-chat-detail", chat.id)
    return render(
        request, "ai_assistance/generic_form.html", {"form": form, "heading": "New Story Chat"}
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chat_detail(request, chat_id):
    workspace = workspace_for(request)
    chat = get_object_or_404(AIChatSession, id=chat_id, workspace=workspace)
    form = ChatMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        author = AIChatMessage.objects.create(
            session=chat, role="author", content=form.cleaned_data["content"]
        )
        try:
            creative_request_obj, suggestion = run_creative_request(
                account=request.user,
                workspace=workspace,
                task_key="story_chat",
                instruction=author.content,
                pack=chat.context_pack,
                chat_messages=chat.messages.exclude(id=author.id),
            )
        except TerminalAdapterError:
            author.provenance = {"provider_error": True}
            author.save(update_fields=("provenance",))
        else:
            AIChatMessage.objects.create(
                session=chat,
                role="assistant",
                content=suggestion.reviewed_output,
                request=creative_request_obj,
                suggestion=suggestion,
                provenance={
                    "context_hash": creative_request_obj.context_hash,
                    "snapshot": creative_request_obj.context_snapshot,
                },
            )
        return redirect("ai-chat-detail", chat.id)
    return render(
        request,
        "ai_assistance/chat.html",
        {"chat": chat, "form": form, "provider_available": provider_available()},
    )


@login_required
@require_POST
def chat_transition(request, chat_id):
    workspace = workspace_for(request)
    chat = get_object_or_404(AIChatSession, id=chat_id, workspace=workspace)
    status = request.POST.get("status")
    if status not in ("active", "archived"):
        raise Http404
    chat.status = status
    chat.save(update_fields=("status", "updated_at"))
    return redirect("ai-chat-detail", chat.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def voice_profile(request, profile_id=None):
    workspace = workspace_for(request)
    profile = (
        get_object_or_404(VoiceProfile, id=profile_id, workspace=workspace) if profile_id else None
    )
    form = VoiceProfileForm(request.POST or None, instance=profile, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.workspace = workspace
        profile.full_clean()
        profile.save()
        return redirect("ai-voice-profile", profile.id)
    return render(
        request, "ai_assistance/generic_form.html", {"form": form, "heading": "Voice Profile"}
    )


@never_cache
@login_required
def ai_history(request):
    workspace = workspace_for(request)
    requests = workspace.ai_creative_requests.select_related("context_pack", "requested_by")
    if state := request.GET.get("state"):
        requests = requests.filter(state=state)
    if task := request.GET.get("task"):
        requests = requests.filter(task_key=task)
    return render(request, "ai_assistance/history.html", {"requests": requests, "tasks": TASKS})
