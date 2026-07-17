from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from ai_assistance.search import search_ai_workspace
from characters.search import search_character_groups, search_characters
from continuity.search import search_continuity
from decks.search import search_cards, search_draws
from scenes.search import search_scenes
from scenes.search_forms import SceneSearchForm
from stories.search import search_chapters, search_works
from timeline.search import search_timeline
from workspaces.services import resolve_owner_workspace
from worldbuilding.search import search_world


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def scene_search(request: HttpRequest) -> HttpResponse:
    workspace = resolve_owner_workspace(request.user)
    form = SceneSearchForm(request.POST or None)
    scene_results = []
    character_results = []
    group_results = []
    work_results = []
    chapter_results = []
    world_results = {
        key: []
        for key in (
            "location_results",
            "region_results",
            "codex_results",
            "item_results",
            "creature_results",
        )
    }
    card_results = []
    draw_results = []
    continuity_results = {
        key: [] for key in ("thread_results", "secret_results", "clue_results", "reveal_results")
    }
    timeline_results = {"timeline_results": [], "timeline_event_results": []}
    ai_results = {"ai_chat_results": [], "ai_context_pack_results": [], "ai_suggestion_results": []}
    searched = request.method == "POST"
    if searched and form.is_valid():
        scene_results = search_scenes(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
            include_archived=form.cleaned_data["include_archived"],
        )
        character_results = search_characters(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
        )
        group_results = search_character_groups(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
        )
        work_results = search_works(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
        )
        chapter_results = search_chapters(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
        )
        world_results = search_world(
            actor=request.user, workspace_id=workspace.id, query_text=form.cleaned_data["query"]
        )
        card_results = search_cards(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
            include_pending=request.POST.get("include_pending_cards") == "1",
        )
        draw_results = search_draws(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
        )
        continuity_results = search_continuity(
            actor=request.user, workspace_id=workspace.id, query_text=form.cleaned_data["query"]
        )
        timeline_results = search_timeline(
            actor=request.user, workspace_id=workspace.id, query_text=form.cleaned_data["query"]
        )
        ai_results = search_ai_workspace(
            actor=request.user, workspace_id=workspace.id, query_text=form.cleaned_data["query"]
        )
    status = 422 if searched and not form.is_valid() else 200
    return render(
        request,
        "scenes/search.html",
        {
            "form": form,
            "results": scene_results,
            "scene_results": scene_results,
            "character_results": character_results,
            "group_results": group_results,
            "work_results": work_results,
            "chapter_results": chapter_results,
            **world_results,
            "card_results": card_results,
            "draw_results": draw_results,
            **continuity_results,
            **timeline_results,
            **ai_results,
            "result_count": (
                len(scene_results)
                + len(character_results)
                + len(group_results)
                + len(work_results)
                + len(chapter_results)
                + sum(len(items) for items in world_results.values())
                + len(card_results)
                + len(draw_results)
                + sum(len(items) for items in continuity_results.values())
                + sum(len(items) for items in timeline_results.values())
                + sum(len(items) for items in ai_results.values())
            ),
            "searched": searched,
        },
        status=status,
    )
