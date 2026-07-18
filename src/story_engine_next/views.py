import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Q
from django.http import Http404, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from ai_assistance.adapters import TerminalAdapterError
from ai_assistance.brainstorm import MODES, instruction_for
from ai_assistance.creative_services import (
    convert_suggestion,
    provider_available,
    run_creative_request,
)
from ai_assistance.models import (
    AIChatMessage,
    AIChatSession,
    AIContextCardLink,
    AIContextCharacterLink,
    AIContextPack,
    AICreativeSuggestion,
    BrainstormSession,
    VoiceProfile,
)
from characters.models import (
    BorrowedAbilityLog,
    Character,
    CharacterAIFieldProposal,
    CharacterGroup,
    CharacterRelationship,
)
from continuity.models import PlotThread
from decks.models import DeckCard, DeckCategory
from publishing.models import ExportRecord, ManuscriptProject, PublicationEntry
from scenes.exceptions import OptimisticConcurrencyConflict
from scenes.models import Scene
from scenes.save_requests import save_scene_content
from stories.models import Chapter, Work
from story_engine_next.models import BrainstormCardSelection, WorldBibleEntry
from timeline.models import TimelineEvent
from workspaces.services import resolve_owner_workspace
from worldbuilding.models import CodexEntry, Location, Region, WorldItem


def _workspace(request):
    return resolve_owner_workspace(request.user)


def _body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


@never_cache
@login_required
def app_shell(request, route=""):
    get_token(request)
    return render(request, "story_engine_next/app.html")


@login_required
def dashboard_api(request):
    workspace = _workspace(request)
    work = Work.objects.filter(workspace=workspace).order_by("-updated_at").first()
    chapters = list((work.chapters.order_by("order")[:6]) if work else [])
    return JsonResponse(
        {
            "greeting": "Your story world is ready.",
            "activeWork": {"id": str(work.id), "title": work.title} if work else None,
            "chapters": [
                {
                    "id": str(c.id),
                    "title": c.title,
                    "status": c.get_status_display(),
                    "words": sum(
                        (len(s.current_revision.content.split()) if s.current_revision else 0)
                        for s in c.scenes.select_related("current_revision")
                    ),
                }
                for c in chapters
            ],
            "threads": [
                {"id": str(t.id), "title": t.title, "priority": t.get_priority_display()}
                for t in PlotThread.objects.filter(workspace=workspace).exclude(
                    status__in=("resolved", "abandoned", "superseded")
                )[:5]
            ],
            "counts": {
                "characters": Character.objects.filter(workspace=workspace).count(),
                "locations": workspace.locations.count(),
                "factions": workspace.character_groups.count(),
                "codex": workspace.codex_entries.count(),
            },
            "wordsToday": 0,
            "streak": 0,
        }
    )


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def character_borrow_api(request, character_id, membership_id, log_id=None):
    workspace = _workspace(request)
    character = get_object_or_404(Character, workspace=workspace, id=character_id)
    membership = get_object_or_404(
        character.mechanic_memberships, workspace=workspace, id=membership_id
    )
    if request.method == "GET":
        work_ids = character.scenes.values_list("work_id", flat=True)
        chapters = Chapter.objects.filter(work_id__in=work_ids).distinct()
        return JsonResponse(
            {
                "characters": [
                    {
                        "id": str(x.id),
                        "name": x.name,
                        "abilities": [{"id": str(a.id), "name": a.name} for a in x.abilities.all()],
                    }
                    for x in Character.objects.filter(workspace=workspace).exclude(id=character.id)
                ],
                "chapters": [
                    {
                        "id": str(x.id),
                        "title": x.title,
                        "scenes": [{"id": str(s.id), "title": s.title} for s in x.scenes.all()],
                    }
                    for x in chapters.prefetch_related("scenes")
                ],
            }
        )
    if request.method == "DELETE":
        get_object_or_404(
            BorrowedAbilityLog,
            workspace=workspace,
            membership=membership,
            id=log_id,
        ).delete()
        return JsonResponse({"deleted": True})
    data = _body(request)
    source = get_object_or_404(Character, workspace=workspace, id=data.get("borrowedFrom"))
    ability = source.abilities.filter(id=data.get("ability") or None).first()
    chapter = Chapter.objects.filter(workspace=workspace, id=data.get("chapter") or None).first()
    scene = Scene.objects.filter(workspace=workspace, id=data.get("scene") or None).first()
    log = BorrowedAbilityLog(
        workspace=workspace,
        membership=membership,
        borrowed_from=source,
        ability=ability,
        ability_name=str(data.get("abilityName") or (ability.name if ability else "")).strip(),
        chapter=chapter,
        scene=scene,
        story_time=str(data.get("storyTime", "")),
        cost_or_damage=str(data.get("cost", "")),
        duration=str(data.get("duration", "")),
        reduced_effectiveness=str(data.get("reducedEffectiveness", "")),
        limitation_triggered=str(data.get("limitation", "")),
        recovery=str(data.get("recovery", "")),
        lasting_consequence=str(data.get("consequence", "")),
        continuity_implications=str(data.get("continuity", "")),
        notes=str(data.get("notes", "")),
    )
    if not log.ability_name:
        return JsonResponse({"error": "Name the borrowed Ability."}, status=400)
    log.full_clean()
    log.save()
    return JsonResponse({"id": str(log.id)}, status=201)


@login_required
def module_api(request, kind):
    workspace = _workspace(request)
    if kind == "items":
        source = WorldItem.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.name,
                x.get_item_type_display(),
                x.get_status_display(),
                x.description,
                f"/world/items/{x.id}/",
            )
            for x in source
        ]
    elif kind == "locations":
        source = Location.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.name,
                x.get_location_type_display(),
                x.get_status_display(),
                x.description,
                f"/world/locations/{x.id}/",
            )
            for x in source
        ]
    elif kind == "timeline":
        source = TimelineEvent.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.title,
                x.display_date or x.era_label or "Date unknown",
                x.get_status_display(),
                x.short_summary or x.description,
                f"/timeline/events/{x.id}/",
            )
            for x in source
        ]
    elif kind == "plot-threads":
        source = PlotThread.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.title,
                x.get_thread_type_display(),
                x.get_status_display(),
                x.short_summary,
                f"/continuity/threads/{x.id}/",
            )
            for x in source
        ]
    elif kind == "voice-profile":
        source = VoiceProfile.objects.filter(workspace=workspace).select_related("work")
        rows = [
            _module_row(
                x,
                x.name,
                x.work.title if x.work_id else "Workspace voice",
                x.get_status_display(),
                x.description or x.prose_guidance,
                f"/ai/voice-profiles/{x.id}/",
            )
            for x in source
        ]
    elif kind == "publication":
        source = PublicationEntry.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.public_title,
                x.get_publication_type_display(),
                x.get_status_display(),
                x.notes,
                f"/publishing/queue/{x.id}/",
            )
            for x in source
        ]
    elif kind == "manuscripts":
        source = ManuscriptProject.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.name,
                x.get_manuscript_type_display(),
                x.get_status_display(),
                x.description,
                f"/publishing/manuscripts/{x.id}/",
            )
            for x in source
        ]
    elif kind == "exports":
        source = ExportRecord.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.filename,
                x.get_export_format_display(),
                x.get_status_display(),
                f"{x.file_size or 0} bytes",
                f"/publishing/exports/{x.id}/",
            )
            for x in source
        ]
    elif kind == "cross-reference":
        source = Character.objects.filter(workspace=workspace)
        rows = [
            _module_row(
                x,
                x.name,
                x.role,
                x.status,
                f"{x.scene_links.count()} Scene appearances",
                f"/story-engine-next/characters/{x.id}/appearances",
            )
            for x in source
        ]
    else:
        raise Http404
    return JsonResponse({"rows": rows})


def _module_row(record, title, meta, status, body, url):
    return {
        "id": str(record.id),
        "title": title,
        "meta": meta,
        "status": status,
        "body": body,
        "url": url,
    }


@login_required
def search_api(request):
    workspace = _workspace(request)
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        sets = (
            (
                "Work",
                Work.objects.filter(workspace=workspace, title__icontains=query)[:10],
                "title",
                "premise",
                lambda x: f"/works/{x.id}/",
            ),
            (
                "Chapter",
                Chapter.objects.filter(workspace=workspace, title__icontains=query)[:10],
                "title",
                "summary",
                lambda x: f"/story-engine-next/story/{x.id}/outline",
            ),
            (
                "Character",
                Character.objects.filter(workspace=workspace, name__icontains=query)[:10],
                "name",
                "summary",
                lambda x: f"/story-engine-next/characters/{x.id}/overview",
            ),
            (
                "Location",
                Location.objects.filter(workspace=workspace, name__icontains=query)[:10],
                "name",
                "description",
                lambda x: f"/world/locations/{x.id}/",
            ),
            (
                "Plot Thread",
                PlotThread.objects.filter(workspace=workspace, title__icontains=query)[:10],
                "title",
                "short_summary",
                lambda x: f"/continuity/threads/{x.id}/",
            ),
        )
        for kind, records, title_field, snippet_field, route in sets:
            results.extend(
                {
                    "type": kind,
                    "title": getattr(x, title_field),
                    "snippet": getattr(x, snippet_field)[:220],
                    "url": route(x),
                }
                for x in records
            )
        for entry in WorldBibleEntry.objects.filter(workspace=workspace).filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )[:10]:
            results.append(
                {
                    "type": "World Bible",
                    "title": entry.title,
                    "snippet": entry.content[:220],
                    "url": "/story-engine-next/world-bible",
                }
            )
    return JsonResponse({"query": query, "results": results})


def _session(workspace, session_id):
    return get_object_or_404(
        BrainstormSession.objects.select_related(
            "context_pack", "work", "chapter", "latest_suggestion"
        ),
        workspace=workspace,
        id=session_id,
    )


def _card_label(selection):
    if selection.card_id:
        return selection.card.prompt or selection.card.title or "Untitled Card"
    return selection.manual_text


def _serialize(session):
    workspace = session.workspace
    result = session.latest_suggestion
    return {
        "id": str(session.id),
        "title": session.title,
        "mode": session.mode,
        "modes": [{"value": key, "label": mode.title} for key, mode in MODES.items()],
        "cards": [
            {
                "id": str(x.id),
                "label": _card_label(x),
                "category": x.card.category.name
                if x.card_id and x.card.category_id
                else ("Manual Card" if not x.card_id else "Card"),
                "manual": not bool(x.card_id),
            }
            for x in session.card_selections.select_related("card__category")
        ],
        "characters": [
            {"id": str(c.id), "name": c.name} for c in Character.objects.filter(workspace=workspace)
        ],
        "selectedCharacterIds": [
            str(x.character_id) for x in session.context_pack.aicontextcharacterlink_set.all()
        ],
        "categories": [
            {"id": str(c.id), "name": c.name}
            for c in DeckCategory.objects.filter(deck__workspace=workspace)
            .order_by("name")
            .distinct()
        ],
        "focus": session.focus,
        "exclusions": session.exclusions,
        "authorNotes": session.author_notes,
        "result": {"id": str(result.id), "text": result.reviewed_output, "state": result.state}
        if result
        else None,
        "providerAvailable": provider_available(),
    }


@login_required
@require_http_methods(["GET", "POST"])
def brainstorm_collection_api(request):
    workspace = _workspace(request)
    if request.method == "POST":
        mode = _body(request).get("mode", "plot")
        if mode not in MODES:
            raise Http404
        work = Work.objects.filter(workspace=workspace).order_by("-updated_at").first()
        pack = AIContextPack.objects.create(
            workspace=workspace, name="Brainstorm context", status="active", work=work
        )
        session = BrainstormSession.objects.create(
            workspace=workspace, title="New Brainstorm", mode=mode, work=work, context_pack=pack
        )
        return JsonResponse({"id": str(session.id)}, status=201)
    sessions = BrainstormSession.objects.filter(workspace=workspace).select_related(
        "latest_suggestion"
    )
    return JsonResponse(
        {
            "sessions": [
                {
                    "id": str(x.id),
                    "title": x.title,
                    "modeLabel": MODES[x.mode].title,
                    "updatedAt": x.updated_at.strftime("%b %-d, %Y"),
                    "hasResult": bool(x.latest_suggestion_id),
                }
                for x in sessions
            ]
        }
    )


@login_required
@require_http_methods(["GET", "PATCH"])
def brainstorm_api(request, session_id):
    workspace = _workspace(request)
    session = _session(workspace, session_id)
    if request.method == "PATCH":
        data = _body(request)
        for api_name, field in (
            ("title", "title"),
            ("focus", "focus"),
            ("exclusions", "exclusions"),
            ("authorNotes", "author_notes"),
        ):
            if api_name in data:
                setattr(session, field, str(data[api_name])[:10000])
        if data.get("mode") in MODES:
            session.mode = data["mode"]
        session.save()
        pack = session.context_pack
        pack.work = session.work
        pack.exclusions = session.exclusions
        pack.author_instructions = session.focus
        pack.save()
        if data.get("toggleCharacter"):
            character = get_object_or_404(
                Character, workspace=workspace, id=data.get("characterId")
            )
            link = pack.aicontextcharacterlink_set.filter(character=character).first()
            if link:
                link.delete()
            else:
                AIContextCharacterLink.objects.create(
                    pack=pack,
                    character=character,
                    role="Characters in This Session",
                    priority=10,
                    order=pack.aicontextcharacterlink_set.count(),
                )
        if "reviewedOutput" in data and session.latest_suggestion_id:
            suggestion = session.latest_suggestion
            suggestion.reviewed_output = str(data["reviewedOutput"])
            suggestion.state = "editing"
            suggestion.save(update_fields=("reviewed_output", "state"))
    return JsonResponse(_serialize(session))


@login_required
@require_http_methods(["POST"])
@transaction.atomic
def brainstorm_draw_api(request, session_id):
    workspace = _workspace(request)
    session = _session(workspace, session_id)
    data = _body(request)
    count = int(data.get("count", 5))
    if count not in (3, 5, 7, 10):
        return JsonResponse({"error": "Choose 3, 5, 7, or 10 Cards."}, status=400)
    cards = DeckCard.objects.filter(deck__workspace=workspace, is_active=True).exclude(
        review_status__in=("rejected_duplicate", "intentionally_excluded")
    )
    category_ids = data.get("categories") or []
    if category_ids:
        cards = cards.filter(category_id__in=category_ids)
    chosen = list(cards.order_by("?")[:count])
    if len(chosen) < count:
        return JsonResponse({"error": "Not enough eligible Cards are available."}, status=400)
    session.card_selections.all().delete()
    BrainstormCardSelection.objects.bulk_create(
        [
            BrainstormCardSelection(session=session, card=card, order=i)
            for i, card in enumerate(chosen)
        ]
    )
    return JsonResponse(_serialize(session))


@login_required
@require_http_methods(["POST", "DELETE"])
def brainstorm_card_api(request, session_id, selection_id=None):
    workspace = _workspace(request)
    session = _session(workspace, session_id)
    if request.method == "DELETE":
        get_object_or_404(session.card_selections, id=selection_id).delete()
    else:
        text = str(_body(request).get("text", "")).strip()
        if not text:
            return JsonResponse({"error": "Enter a Card."}, status=400)
        maximum = session.card_selections.aggregate(Max("order"))["order__max"]
        BrainstormCardSelection.objects.create(
            session=session,
            manual_text=text[:1000],
            order=0 if maximum is None else maximum + 1,
        )
    return JsonResponse(_serialize(session))


@login_required
@require_http_methods(["POST"])
def brainstorm_generate_api(request, session_id):
    workspace = _workspace(request)
    session = _session(workspace, session_id)
    pack = session.context_pack
    pack.aicontextcardlink_set.all().delete()
    for order, selection in enumerate(session.card_selections.exclude(card=None)):
        AIContextCardLink.objects.create(
            pack=pack, card=selection.card, role="Story Engine Card", priority=5, order=order
        )
    manual = [x.manual_text for x in session.card_selections.filter(card=None)]
    instruction = instruction_for(session) + (
        ("\n\nMANUAL CARDS:\n- " + "\n- ".join(manual)) if manual else ""
    )
    try:
        _, suggestion = run_creative_request(
            account=request.user,
            workspace=workspace,
            task_key=MODES[session.mode].task_key,
            instruction=instruction,
            pack=pack,
        )
    except TerminalAdapterError:
        return JsonResponse({"error": "The provider returned no usable result."}, status=502)
    session.latest_suggestion = suggestion
    session.save(update_fields=("latest_suggestion", "updated_at"))
    return JsonResponse(_serialize(session))


@login_required
@require_http_methods(["POST"])
def apply_suggestion_api(request, suggestion_id):
    workspace = _workspace(request)
    suggestion = get_object_or_404(AICreativeSuggestion, workspace=workspace, id=suggestion_id)
    data = _body(request)
    destination = data.get("destination")
    mapped = {
        "world_bible": "world_bible",
        "codex": "codex",
        "character_note": "character_note",
        "location": "location",
        "item": "item",
        "plot_thread": "plot_thread",
        "chapter_outline": "chapter_outline",
    }.get(destination)
    if not mapped:
        return JsonResponse({"error": "That destination is not available yet."}, status=400)
    suggestion.reviewed_output = str(data.get("content", ""))
    suggestion.state = "accepted"
    suggestion.save(update_fields=("reviewed_output", "state"))
    target = None
    action = "create"
    if mapped == "chapter_outline":
        target = (
            suggestion.request.context_pack.chapter if suggestion.request.context_pack_id else None
        )
        action = "append"
        if target is None:
            return JsonResponse(
                {"error": "Select a Chapter before applying to its outline."}, status=400
            )
    elif mapped == "character_note":
        target = get_object_or_404(Character, workspace=workspace, id=data.get("targetId"))
        action = "append"
    created = convert_suggestion(
        suggestion,
        target_type=mapped,
        title=str(data.get("title", "New story element"))[:240],
        content=suggestion.reviewed_output,
        action=action,
        target=target,
    )
    routes = {
        "location": f"/world/locations/{created.id}/",
        "item": f"/world/items/{created.id}/",
        "plot_thread": f"/continuity/threads/{created.id}/",
        "chapter_outline": f"/stories/chapters/{created.id}/#outline",
        "region": f"/world/regions/{created.id}/",
        "world_bible": f"/story-engine-next/world-bible/{created.id}",
        "codex": f"/world/codex/{created.id}/",
        "character_note": f"/story-engine-next/characters/{created.id}/overview",
    }
    return JsonResponse({"label": str(created), "url": routes[mapped]})


def _serialize_chat(session):
    return {
        "id": str(session.id),
        "title": session.title,
        "work": session.work.title if session.work_id else "No active Work",
        "status": session.status,
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "suggestionId": str(message.suggestion_id) if message.suggestion_id else None,
            }
            for message in session.messages.all()
        ],
    }


@login_required
@require_http_methods(["GET", "POST"])
def chat_collection_api(request):
    workspace = _workspace(request)
    if request.method == "POST":
        work = Work.objects.filter(workspace=workspace).order_by("-updated_at").first()
        pack = AIContextPack.objects.create(
            workspace=workspace, name="Story Chat context", status="active", work=work
        )
        session = AIChatSession.objects.create(
            workspace=workspace,
            title="New Story Chat",
            context_pack=pack,
            work=work,
        )
        return JsonResponse(_serialize_chat(session), status=201)
    sessions = AIChatSession.objects.filter(workspace=workspace)
    return JsonResponse(
        {
            "sessions": [
                {"id": str(session.id), "title": session.title, "status": session.status}
                for session in sessions
            ]
        }
    )


@login_required
@require_http_methods(["GET", "PATCH"])
def chat_api(request, session_id):
    workspace = _workspace(request)
    session = get_object_or_404(AIChatSession, workspace=workspace, id=session_id)
    if request.method == "PATCH":
        data = _body(request)
        if data.get("title"):
            session.title = str(data["title"])[:240]
        if data.get("status") in ("active", "archived"):
            session.status = data["status"]
        session.save()
    return JsonResponse(_serialize_chat(session))


@login_required
@require_http_methods(["POST"])
def chat_message_api(request, session_id):
    workspace = _workspace(request)
    session = get_object_or_404(
        AIChatSession.objects.select_related("context_pack"), workspace=workspace, id=session_id
    )
    content = str(_body(request).get("content", "")).strip()
    if not content:
        return JsonResponse({"error": "Enter a message."}, status=400)
    history = tuple((message.role, message.content) for message in session.messages.all())
    AIChatMessage.objects.create(session=session, role="author", content=content)
    try:
        request_obj, suggestion = run_creative_request(
            account=request.user,
            workspace=workspace,
            task_key="story_chat",
            instruction=content,
            pack=session.context_pack,
            chat_messages=history,
        )
    except TerminalAdapterError:
        return JsonResponse({"error": "The provider returned no usable response."}, status=502)
    AIChatMessage.objects.create(
        session=session,
        role="assistant",
        content=suggestion.reviewed_output,
        provenance={"context_hash": request_obj.context_hash},
        request=request_obj,
        suggestion=suggestion,
    )
    session.save(update_fields=("updated_at",))
    return JsonResponse(_serialize_chat(session))


CHARACTER_FIELDS = {
    "overview": (
        "name",
        "aliases",
        "role",
        "age",
        "status",
        "tags",
        "summary",
        "goals",
        "internal_conflict",
        "external_conflict",
        "current_story_function",
    ),
    "appearance": (
        "appearance",
        "distinctive_features",
        "clothing",
        "mannerisms",
        "sensory_presence",
    ),
    "personality": (
        "personality",
        "temperament",
        "values",
        "fears",
        "wants",
        "contradictions",
        "habits",
    ),
    "backstory": ("backstory", "origins", "formative_events"),
    "arc-notes": (
        "intended_arc",
        "current_arc_phase",
        "arc_turning_points",
        "arc_questions",
        "arc_predictions",
    ),
    "evaluation": ("evaluation_notes",),
}


def _character_payload(character):
    relationships = (
        CharacterRelationship.objects.filter(workspace=character.workspace)
        .filter(Q(source=character) | Q(target=character))
        .select_related("source", "target")
    )
    memberships = character.group_memberships.select_related("group")
    mechanics = character.mechanic_memberships.select_related(
        "template", "family_group"
    ).prefetch_related(
        "template__shared_abilities",
        "borrowing_log__borrowed_from",
        "borrowing_log__chapter",
        "borrowing_log__scene",
    )
    return {
        "id": str(character.id),
        "name": character.name,
        "status": character.status or "Active",
        "fields": {
            field: getattr(character, field)
            for fields in CHARACTER_FIELDS.values()
            for field in fields
        },
        "traits": [
            {
                "id": str(x.id),
                "name": x.name,
                "score": x.score,
                "low": x.low_label,
                "high": x.high_label,
            }
            for x in character.personality_traits.all()
        ],
        "abilities": [
            {
                "id": str(x.id),
                "name": x.name,
                "description": x.description,
                "limitations": x.limitations,
                "costs": x.costs,
                "mastery": x.get_mastery_display(),
                "status": x.get_status_display(),
                "stages": [
                    {"name": s.name, "state": s.get_state_display()} for s in x.stages.all()
                ],
            }
            for x in character.abilities.prefetch_related("stages")
        ],
        "relationships": [
            {
                "id": str(x.id),
                "otherId": str(x.target_id if x.source_id == character.id else x.source_id),
                "other": x.target.name if x.source_id == character.id else x.source.name,
                "type": x.get_relationship_type_display(),
                "summary": x.summary,
                "status": x.get_status_display(),
            }
            for x in relationships
        ],
        "families": [
            {
                "id": str(x.group_id),
                "name": x.group.name,
                "role": x.role,
                "status": x.get_status_display(),
            }
            for x in memberships
            if x.group.group_type == "family"
        ],
        "groups": [
            {
                "id": str(x.group_id),
                "name": x.group.name,
                "role": x.role,
                "status": x.get_status_display(),
            }
            for x in memberships
            if x.group.group_type != "family"
        ],
        "mechanics": [
            {
                "id": str(m.id),
                "name": m.template.name,
                "designationLabel": m.template.designation_label,
                "designation": m.designation,
                "family": m.family_group.name if m.family_group_id else "",
                "rules": m.template.borrowing_rules,
                "shared": [
                    {"name": a.name, "description": a.description, "limitations": a.limitations}
                    for a in m.template.shared_abilities.all()
                ],
                "logs": [
                    {
                        "id": str(log.id),
                        "from": log.borrowed_from.name,
                        "ability": log.ability_name,
                        "chapter": log.chapter.title if log.chapter_id else "",
                        "scene": log.scene.title if log.scene_id else "",
                        "cost": log.cost_or_damage,
                        "duration": log.duration,
                        "consequence": log.lasting_consequence,
                        "notes": log.notes,
                    }
                    for log in m.borrowing_log.all()
                ],
            }
            for m in mechanics
        ],
        "appearances": [
            {
                "id": str(link.scene_id),
                "scene": link.scene.title,
                "chapter": link.scene.chapter.title if link.scene.chapter_id else "Unassigned",
                "work": link.scene.work.title if link.scene.work_id else "",
                "pov": bool(
                    link.scene.chapter_id and link.scene.chapter.pov_character_id == character.id
                ),
            }
            for link in character.scene_links.select_related("scene__chapter", "scene__work")
        ],
    }


@login_required
@require_http_methods(["GET", "POST"])
def character_collection_api(request):
    workspace = _workspace(request)
    if request.method == "POST":
        name = str(_body(request).get("name", "")).strip()
        if not name:
            return JsonResponse({"error": "Enter a Character name."}, status=400)
        character = Character.objects.create(workspace=workspace, name=name[:200])
        return JsonResponse({"id": str(character.id)}, status=201)
    return JsonResponse(
        {
            "characters": [
                {
                    "id": str(x.id),
                    "name": x.name,
                    "role": x.role,
                    "status": x.status,
                    "summary": x.summary,
                    "abilities": x.abilities.count(),
                    "appearances": x.scene_links.count(),
                }
                for x in Character.objects.filter(workspace=workspace)
            ]
        }
    )


@login_required
@require_http_methods(["GET", "PATCH"])
def character_api(request, character_id):
    workspace = _workspace(request)
    character = get_object_or_404(Character, workspace=workspace, id=character_id)
    if request.method == "PATCH":
        data = _body(request)
        allowed = {field for fields in CHARACTER_FIELDS.values() for field in fields}
        changed = []
        for field, value in data.items():
            if field in allowed:
                setattr(character, field, str(value)[:100000])
                changed.append(field)
        if changed:
            character.full_clean()
            character.save(update_fields=(*changed, "updated_at"))
    return JsonResponse(_character_payload(character))


def _character_pack(workspace, character):
    name = f"Character · {character.name} · {str(character.id)[:8]}"
    pack, _ = AIContextPack.objects.get_or_create(
        workspace=workspace,
        name=name,
        defaults={
            "description": "Character-scoped context.",
            "status": "active",
            "detail_level": "detailed",
        },
    )
    AIContextCharacterLink.objects.get_or_create(
        pack=pack,
        character=character,
        defaults={"role": "Primary Character", "priority": 1},
    )
    return pack


def _chapter_pack(workspace, chapter):
    name = f"Chapter · {chapter.title} · {str(chapter.id)[:8]}"
    pack, _ = AIContextPack.objects.get_or_create(
        workspace=workspace,
        name=name,
        defaults={
            "description": "Story Workshop context.",
            "work": chapter.work,
            "chapter": chapter,
            "status": "active",
            "detail_level": "detailed",
        },
    )
    changed = []
    if pack.work_id != chapter.work_id:
        pack.work = chapter.work
        changed.append("work")
    if pack.chapter_id != chapter.id:
        pack.chapter = chapter
        changed.append("chapter")
    if changed:
        pack.save(update_fields=(*changed, "updated_at"))
    return pack


@login_required
@require_http_methods(["POST", "PATCH"])
def character_fill_api(request, character_id):
    workspace = _workspace(request)
    character = get_object_or_404(Character, workspace=workspace, id=character_id)
    data = _body(request)
    if request.method == "POST":
        description = str(data.get("description", "")).strip()
        if not description:
            return JsonResponse({"error": "Add a description first."}, status=400)
        _, suggestion = run_creative_request(
            account=request.user,
            workspace=workspace,
            task_key="character_fill_description",
            instruction="Extract only supported details. Do not invent missing facts.\n\n"
            + description,
            pack=_character_pack(workspace, character),
        )
        mapping = {
            "Name": "name",
            "Aliases": "aliases",
            "Role": "role",
            "Age": "age",
            "Appearance": "appearance",
            "Personality": "personality",
            "Backstory": "backstory",
            "Goals": "goals",
            "Conflicts": "internal_conflict",
            "Voice": "voice_notes",
            "Tags": "tags",
        }
        values = {
            field: suggestion.structured_output.get(label, "")
            for label, field in mapping.items()
            if suggestion.structured_output.get(label)
        }
        proposal = CharacterAIFieldProposal.objects.create(
            workspace=workspace,
            character=character,
            suggestion=suggestion,
            description=description,
            proposed_values=values,
        )
    else:
        proposal = get_object_or_404(
            CharacterAIFieldProposal,
            workspace=workspace,
            character=character,
            id=data.get("proposalId"),
        )
        selected = [field for field in data.get("fields", []) if field in proposal.proposed_values]
        for field in selected:
            setattr(character, field, proposal.proposed_values[field])
        if selected:
            character.full_clean()
            character.save(update_fields=(*selected, "updated_at"))
        proposal.applied_fields = selected
        proposal.save(update_fields=("applied_fields",))
        proposal.suggestion.state = "converted"
        proposal.suggestion.save(update_fields=("state",))
    return JsonResponse(
        {
            "proposalId": str(proposal.id),
            "rows": [
                {
                    "field": field,
                    "label": field.replace("_", " ").title(),
                    "existing": getattr(character, field, ""),
                    "proposed": value,
                }
                for field, value in proposal.proposed_values.items()
            ],
        }
    )


@login_required
@require_http_methods(["GET", "POST"])
def character_assist_api(request, character_id):
    workspace = _workspace(request)
    character = get_object_or_404(Character, workspace=workspace, id=character_id)
    actions = (
        ("character_deepen", "Deepen this Character"),
        ("character_goals", "Generate goals and conflicts"),
        ("character_backstory", "Develop backstory"),
        ("character_personality", "Refine personality"),
        ("character_sliders", "Suggest sliders"),
        ("character_voice", "Evaluate Character voice"),
        ("character_relationships", "Assess relationship dynamics"),
        ("character_arc", "Propose arc progression"),
        ("character_evaluation", "Generate an evaluation"),
        ("character_continuity", "Identify continuity risks"),
        ("ability_consistency", "Assess abilities and limitations"),
    )
    if request.method == "GET":
        return JsonResponse({"actions": [{"key": x, "label": y} for x, y in actions]})
    data = _body(request)
    task = data.get("task")
    if task not in {x for x, _ in actions}:
        raise Http404
    _, suggestion = run_creative_request(
        account=request.user,
        workspace=workspace,
        task_key=task,
        instruction=str(
            data.get("instruction")
            or (
                "Review this Character using story evidence. Keep proposals speculative "
                "and name destination sections."
            )
        ),
        pack=_character_pack(workspace, character),
    )
    return JsonResponse(
        {
            "suggestionId": str(suggestion.id),
            "text": suggestion.reviewed_output,
            "state": suggestion.state,
        }
    )


@login_required
def family_api(request):
    workspace = _workspace(request)
    families = CharacterGroup.objects.filter(
        workspace=workspace, group_type="family"
    ).prefetch_related("memberships__character")
    return JsonResponse(
        {
            "families": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "tagline": f.tagline,
                    "description": f.description,
                    "history": f.history,
                    "members": [
                        {
                            "id": str(m.character_id),
                            "name": m.character.name,
                            "role": m.role,
                            "status": m.get_status_display(),
                        }
                        for m in f.memberships.all()
                    ],
                }
                for f in families
            ]
        }
    )


@login_required
def relationship_web_api(request):
    workspace = _workspace(request)
    characters = list(Character.objects.filter(workspace=workspace)[:80])
    ids = [x.id for x in characters]
    links = CharacterRelationship.objects.filter(
        workspace=workspace, source_id__in=ids, target_id__in=ids
    ).select_related("source", "target")
    return JsonResponse(
        {
            "nodes": [{"id": str(x.id), "name": x.name, "role": x.role} for x in characters],
            "links": [
                {
                    "id": str(x.id),
                    "source": str(x.source_id),
                    "target": str(x.target_id),
                    "type": x.get_relationship_type_display(),
                    "status": x.get_status_display(),
                }
                for x in links
            ],
        }
    )


@login_required
@require_http_methods(["GET", "POST"])
def world_bible_api(request):
    workspace = _workspace(request)
    if request.method == "POST":
        data = _body(request)
        title = str(data.get("title", "New World Bible Entry")).strip()[:240]
        entry = WorldBibleEntry.objects.create(
            workspace=workspace, title=title, order=workspace.world_bible_entries.count()
        )
        return JsonResponse({"id": str(entry.id)}, status=201)
    return JsonResponse(
        {
            "entries": [
                {"id": str(x.id), "title": x.title, "content": x.content}
                for x in workspace.world_bible_entries.all()
            ]
        }
    )


@login_required
@require_http_methods(["PATCH", "DELETE"])
def world_bible_entry_api(request, entry_id):
    workspace = _workspace(request)
    entry = get_object_or_404(WorldBibleEntry, workspace=workspace, id=entry_id)
    if request.method == "DELETE":
        entry.delete()
        return JsonResponse({"deleted": True})
    data = _body(request)
    if "title" in data:
        entry.title = str(data["title"]).strip()[:240]
    if "content" in data:
        entry.content = str(data["content"])
    entry.full_clean()
    entry.save()
    return JsonResponse({"id": str(entry.id), "title": entry.title, "content": entry.content})


@login_required
def world_api(request):
    workspace = _workspace(request)
    groups = CharacterGroup.objects.filter(workspace=workspace).exclude(group_type="family")
    return JsonResponse(
        {
            "factions": [
                {
                    "id": str(x.id),
                    "name": x.name,
                    "status": x.get_status_display(),
                    "description": x.description,
                    "purpose": x.purpose,
                }
                for x in groups
            ],
            "codex": [
                {
                    "id": str(x.id),
                    "name": x.term,
                    "status": x.get_canon_state_display(),
                    "description": x.definition or x.description,
                }
                for x in CodexEntry.objects.filter(workspace=workspace)
            ],
            "regions": [
                {
                    "id": str(x.id),
                    "name": x.name,
                    "status": x.get_status_display(),
                    "description": x.description,
                }
                for x in Region.objects.filter(workspace=workspace)
            ],
            "locations": [
                {"id": str(x.id), "name": x.name, "status": x.status, "description": x.description}
                for x in Location.objects.filter(workspace=workspace)
            ],
            "items": [
                {
                    "id": str(x.id),
                    "name": x.name,
                    "status": x.get_status_display(),
                    "description": x.description,
                }
                for x in WorldItem.objects.filter(workspace=workspace)
            ],
        }
    )


@login_required
def story_api(request):
    workspace = _workspace(request)
    work = Work.objects.filter(workspace=workspace).order_by("-updated_at").first()
    if not work:
        return JsonResponse({"work": None, "volumes": [], "unassigned": []})
    volumes = []
    for volume in work.volumes.prefetch_related("arcs__chapters", "chapters").all():
        arc_ids = set()
        arcs = []
        for arc in volume.arcs.all():
            chapters = list(arc.chapters.all())
            arc_ids.update(x.id for x in chapters)
            arcs.append(
                {
                    "id": str(arc.id),
                    "title": arc.title,
                    "chapters": [
                        {"id": str(x.id), "title": x.title, "status": x.get_status_display()}
                        for x in chapters
                    ],
                }
            )
        direct = [x for x in volume.chapters.all() if x.id not in arc_ids]
        volumes.append(
            {
                "id": str(volume.id),
                "title": volume.title,
                "arcs": arcs,
                "chapters": [
                    {"id": str(x.id), "title": x.title, "status": x.get_status_display()}
                    for x in direct
                ],
            }
        )
    unassigned = work.chapters.filter(volume=None, arc=None)
    return JsonResponse(
        {
            "work": {"id": str(work.id), "title": work.title},
            "volumes": volumes,
            "unassigned": [
                {"id": str(x.id), "title": x.title, "status": x.get_status_display()}
                for x in unassigned
            ],
        }
    )


def _chapter_payload(chapter):
    scenes = chapter.scenes.select_related("current_revision").order_by(
        "structure_order", "ordering"
    )
    pacing = getattr(chapter, "pacing_profile", None)
    return {
        "id": str(chapter.id),
        "title": chapter.title,
        "label": chapter.label,
        "status": chapter.status,
        "work": {"id": str(chapter.work_id), "title": chapter.work.title},
        "fields": {
            f: getattr(chapter, f)
            for f in (
                "concept",
                "key_beats",
                "emotional_arc",
                "character_focus",
                "goal",
                "brain_dump",
                "outline",
                "editorial_concerns",
                "revision_priorities",
                "unresolved_questions",
                "final_check_notes",
                "notes",
            )
        },
        "scenes": [
            {
                "id": str(x.id),
                "title": x.title,
                "version": x.version,
                "revisionId": str(x.current_revision_id),
                "content": x.current_revision.content if x.current_revision else "",
                "lifecycle": x.lifecycle,
            }
            for x in scenes
        ],
        "beats": [
            {
                "id": str(x.id),
                "title": x.title,
                "type": x.get_beat_type_display(),
                "summary": x.summary,
                "status": x.get_status_display(),
            }
            for x in chapter.structured_beats.all()
        ],
        "pacing": {
            f: getattr(pacing, f) if pacing else None
            for f in (
                "tension_score",
                "dread_score",
                "emotional_intimacy_score",
                "relationship_tension_score",
                "pacing_energy_score",
                "humor_score",
            )
        },
        "briefs": [
            {
                "id": str(b.id),
                "scene": b.scene.title,
                "status": b.get_status_display(),
                "stale": b.is_stale,
                "function": b.scene_function,
                "conflict": b.primary_conflict,
                "stakes": b.stakes,
            }
            for b in chapter.scenes.all()
            for b in b.briefs.filter(status="active")
        ],
        "snapshots": [
            {"id": str(x.id), "label": x.label, "created": x.created_at.strftime("%b %-d, %Y")}
            for x in chapter.planning_snapshots.all()[:10]
        ],
        "threads": [
            {"id": str(x.thread_id), "title": x.thread.title, "role": x.role}
            for x in chapter.thread_links.select_related("thread")
        ],
        "publicationUrl": f"/publishing/queue/?chapter={chapter.id}",
    }


@login_required
@require_http_methods(["GET", "PATCH"])
def chapter_api(request, chapter_id):
    workspace = _workspace(request)
    chapter = get_object_or_404(
        Chapter.objects.select_related("work"), workspace=workspace, id=chapter_id
    )
    if request.method == "PATCH":
        data = _body(request)
        allowed = {
            "concept",
            "key_beats",
            "emotional_arc",
            "character_focus",
            "goal",
            "brain_dump",
            "outline",
            "editorial_concerns",
            "revision_priorities",
            "unresolved_questions",
            "final_check_notes",
            "notes",
            "status",
        }
        changed = []
        for field, value in data.items():
            if field in allowed:
                setattr(chapter, field, str(value))
                changed.append(field)
        if changed:
            chapter.full_clean()
            chapter.save(update_fields=(*changed, "updated_at"))
    return JsonResponse(_chapter_payload(chapter))


@login_required
@require_http_methods(["POST"])
def chapter_stage_api(request, chapter_id):
    workspace = _workspace(request)
    chapter = get_object_or_404(
        Chapter.objects.select_related("work"), workspace=workspace, id=chapter_id
    )
    stage = str(_body(request).get("stage", ""))
    task_key = {
        "outline": "chapter_outline",
        "editor": "editorial_developmental",
        "scene-brief": "scene_brief",
        "de-slop": "deslop_pacing_analysis",
        "continuity": "continuity_review",
        "polish": "editorial_tighten",
    }.get(stage)
    if not task_key:
        return JsonResponse({"error": "That Workshop action is not available."}, status=400)
    instruction = {
        "outline": "Build a Chapter outline from the saved intake and brain dump.",
        "editor": "Review the current Chapter draft. Cite evidence and do not rewrite silently.",
        "scene-brief": "Build a Scene Brief for the current Chapter's next drafting need.",
        "de-slop": "Run the first De-Slop analysis pass against the current draft.",
        "continuity": "Review this Chapter for continuity risks and author questions.",
        "polish": "Propose a voice-preserving polish. Keep original and proposed text distinct.",
    }[stage]
    _, suggestion = run_creative_request(
        account=request.user,
        workspace=workspace,
        task_key=task_key,
        instruction=instruction,
        pack=_chapter_pack(workspace, chapter),
    )
    return JsonResponse(
        {
            "suggestionId": str(suggestion.id),
            "text": suggestion.reviewed_output,
            "stage": stage,
        }
    )


@login_required
@require_http_methods(["POST"])
def scene_save_api(request, scene_id):
    workspace = _workspace(request)
    scene = get_object_or_404(
        Scene.objects.select_related("current_revision"), workspace=workspace, id=scene_id
    )
    data = _body(request)
    try:
        result = save_scene_content(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=scene.current_revision_id,
            expected_scene_version=int(data.get("version", scene.version)),
            proposed_content=str(data.get("content", "")),
            idempotency_key=str(data.get("idempotencyKey", "")),
            save_intent="explicit_save",
        )
    except OptimisticConcurrencyConflict as exc:
        return JsonResponse(
            {
                "error": "This Scene changed in another session.",
                "version": exc.current_scene_version,
                "revisionId": str(exc.current_revision_id),
            },
            status=409,
        )
    return JsonResponse(
        {
            "id": str(scene.id),
            "version": result.scene_version,
            "revisionId": str(result.revision.id),
            "content": result.revision.content,
        }
    )
