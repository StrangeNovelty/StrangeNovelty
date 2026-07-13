import uuid
from typing import cast

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from characters.forms import (
    CharacterCreateForm,
    CharacterForm,
    CharacterListSearchForm,
    CharacterSceneLinkForm,
    SceneCharacterSelectorForm,
)
from characters.models import Character
from characters.search import search_characters
from characters.services import (
    CharacterDomainError,
    CharacterInaccessible,
    create_character,
    link_character_scene,
    sync_scene_characters,
    unlink_character_scene,
    update_character,
)
from scenes.models import Scene
from workspaces.models import Workspace
from workspaces.services import resolve_owner_workspace


def _see_other(location: str) -> HttpResponseRedirect:
    response = HttpResponseRedirect(location)
    response.status_code = 303
    return response


def _request_workspace(request: HttpRequest) -> Workspace:
    return resolve_owner_workspace(request.user)


def _authorized_character(request: HttpRequest, character_id: uuid.UUID) -> Character:
    workspace = _request_workspace(request)
    try:
        return cast(
            Character,
            Character.objects.prefetch_related("scenes").get(id=character_id, workspace=workspace),
        )
    except Character.DoesNotExist as exc:
        raise Http404("Character is unavailable.") from exc


def _detail_context(
    *, request: HttpRequest, character: Character, form: CharacterForm
) -> dict[str, object]:
    workspace = _request_workspace(request)
    scene_links = character.scene_links.select_related("scene").exclude(
        scene__lifecycle=Scene.Lifecycle.TRASHED
    )
    return {
        "character": character,
        "form": form,
        "scene_links": scene_links,
        "scene_link_form": CharacterSceneLinkForm(workspace=workspace, character=character),
    }


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_list(request: HttpRequest) -> HttpResponse:
    workspace = _request_workspace(request)
    form = CharacterListSearchForm(request.POST or None)
    searched = request.method == "POST"
    if searched and form.is_valid():
        characters = [
            result.character
            for result in search_characters(
                actor=request.user,
                workspace_id=workspace.id,
                query_text=form.cleaned_data["query"],
                limit=50,
            )
        ]
    else:
        characters = list(Character.objects.filter(workspace=workspace).order_by("-updated_at"))
    status = 422 if searched and not form.is_valid() else 200
    return render(
        request,
        "characters/list.html",
        {"characters": characters, "form": form, "searched": searched},
        status=status,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_create(request: HttpRequest) -> HttpResponse:
    workspace = _request_workspace(request)
    form = CharacterCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            character = create_character(
                actor=request.user,
                workspace_id=workspace.id,
                values=form.cleaned_data,
            )
        except CharacterDomainError:
            form.add_error(None, "The Character could not be created.")
        else:
            return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    status = 422 if request.method == "POST" else 200
    return render(request, "characters/create.html", {"form": form}, status=status)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def character_detail(request: HttpRequest, character_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    form = CharacterForm(request.POST or None, instance=character)
    if request.method == "POST" and form.is_valid():
        try:
            character = update_character(
                actor=request.user,
                workspace_id=workspace.id,
                character_id=character.id,
                values=form.cleaned_data,
            )
        except CharacterInaccessible as exc:
            raise Http404("Character is unavailable.") from exc
        except CharacterDomainError:
            form.add_error(None, "The Character could not be saved.")
        else:
            return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))
    status = 422 if request.method == "POST" else 200
    return render(
        request,
        "characters/detail.html",
        _detail_context(request=request, character=character, form=form),
        status=status,
    )


@never_cache
@login_required
@require_POST
def character_scene_link(request: HttpRequest, character_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    character = _authorized_character(request, character_id)
    form = CharacterSceneLinkForm(request.POST, workspace=workspace, character=character)
    if not form.is_valid():
        raise Http404("Scene is unavailable.")
    try:
        link_character_scene(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character.id,
            scene_id=form.cleaned_data["scene"].id,
        )
    except CharacterDomainError as exc:
        raise Http404("Scene is unavailable.") from exc
    return _see_other(reverse("character-detail", kwargs={"character_id": character.id}))


@never_cache
@login_required
@require_POST
def character_scene_unlink(
    request: HttpRequest, character_id: uuid.UUID, scene_id: uuid.UUID
) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        unlink_character_scene(
            actor=request.user,
            workspace_id=workspace.id,
            character_id=character_id,
            scene_id=scene_id,
        )
    except CharacterDomainError as exc:
        raise Http404("Character and Scene link is unavailable.") from exc
    return _see_other(reverse("character-detail", kwargs={"character_id": character_id}))


@never_cache
@login_required
@require_POST
def scene_characters_update(request: HttpRequest, scene_id: uuid.UUID) -> HttpResponse:
    workspace = _request_workspace(request)
    try:
        scene = Scene.objects.get(id=scene_id, workspace=workspace)
    except Scene.DoesNotExist as exc:
        raise Http404("Scene is unavailable.") from exc
    if scene.lifecycle != Scene.Lifecycle.ACTIVE:
        raise Http404("Scene is unavailable.")
    form = SceneCharacterSelectorForm(request.POST, workspace=workspace)
    if not form.is_valid():
        raise Http404("One or more Characters are unavailable.")
    try:
        sync_scene_characters(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            character_ids=(character.id for character in form.cleaned_data["characters"]),
        )
    except CharacterDomainError as exc:
        raise Http404("Characters could not be updated.") from exc
    return _see_other(reverse("scene-editor", kwargs={"scene_id": scene.id}))
