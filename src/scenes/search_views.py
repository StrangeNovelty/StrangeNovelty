from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from scenes.search import search_scenes
from scenes.search_forms import SceneSearchForm
from workspaces.services import resolve_owner_workspace


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def scene_search(request: HttpRequest) -> HttpResponse:
    workspace = resolve_owner_workspace(request.user)
    form = SceneSearchForm(request.POST or None)
    results = []
    searched = request.method == "POST"
    if searched and form.is_valid():
        results = search_scenes(
            actor=request.user,
            workspace_id=workspace.id,
            query_text=form.cleaned_data["query"],
            include_archived=form.cleaned_data["include_archived"],
        )
    status = 422 if searched and not form.is_valid() else 200
    return render(
        request,
        "scenes/search.html",
        {"form": form, "results": results, "searched": searched},
        status=status,
    )
