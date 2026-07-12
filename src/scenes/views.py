import uuid
from typing import cast

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from scenes.content import MAX_CONTENT_CHARACTERS
from scenes.exceptions import (
    DomainIntegrityFailure,
    InvalidSceneOrdering,
    InvalidSceneTitle,
    SceneDomainError,
)
from scenes.forms import SceneCreateForm, SceneSaveForm
from scenes.models import Scene
from scenes.save_requests import IdempotencyKeyConflict, SaveRequestOutcome, save_scene_content
from scenes.services import create_scene
from workspaces.services import resolve_owner_workspace

MAX_SAVE_REQUEST_BYTES = MAX_CONTENT_CHARACTERS * 4 + 8192


def _see_other(location: str) -> HttpResponseRedirect:
    response = HttpResponseRedirect(location)
    response.status_code = 303
    return response


def _authorized_scene(request: HttpRequest, scene_id: uuid.UUID) -> Scene:
    workspace = resolve_owner_workspace(request.user)
    try:
        scene = cast(
            Scene,
            Scene.objects.select_related("current_revision").get(id=scene_id, workspace=workspace),
        )
    except Scene.DoesNotExist as exc:
        raise Http404("Scene is unavailable.") from exc
    if scene.lifecycle == Scene.Lifecycle.TRASHED or scene.current_revision is None:
        raise Http404("Scene is unavailable.")
    return scene


@never_cache
@login_required
def scene_list(request: HttpRequest) -> HttpResponse:
    workspace = resolve_owner_workspace(request.user)
    scenes = Scene.objects.filter(workspace=workspace).exclude(lifecycle=Scene.Lifecycle.TRASHED)
    return render(request, "scenes/list.html", {"scenes": scenes})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def scene_create(request: HttpRequest) -> HttpResponse:
    workspace = resolve_owner_workspace(request.user)
    form = SceneCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            result = create_scene(
                actor=request.user,
                workspace_id=workspace.id,
                title=form.cleaned_data["title"],
                ordering=None,
            )
        except InvalidSceneTitle, InvalidSceneOrdering, DomainIntegrityFailure:
            form.add_error(None, "The Scene could not be created.")
        else:
            return _see_other(reverse("scene-editor", kwargs={"scene_id": result.scene.id}))
    status = 422 if request.method == "POST" else 200
    return render(request, "scenes/create.html", {"form": form}, status=status)


@never_cache
@login_required
@require_http_methods(["GET"])
def scene_editor(request: HttpRequest, scene_id: uuid.UUID) -> HttpResponse:
    scene = _authorized_scene(request, scene_id)
    current = scene.current_revision
    if current is None:
        raise Http404("Scene is unavailable.")
    form = SceneSaveForm(
        initial={
            "content": current.content,
            "expected_current_revision_id": current.id,
            "expected_scene_version": scene.version,
            "idempotency_key": uuid.uuid4().hex,
            "save_intent": "explicit_save",
        }
    )
    return render(
        request,
        "scenes/editor.html",
        {"scene": scene, "current_revision": current, "form": form},
    )


@never_cache
@login_required
@require_POST
def scene_save(request: HttpRequest, scene_id: uuid.UUID) -> HttpResponse:
    scene = _authorized_scene(request, scene_id)
    if scene.lifecycle != Scene.Lifecycle.ACTIVE:
        raise Http404("Scene is unavailable.")

    content_length = request.META.get("CONTENT_LENGTH")
    if content_length:
        try:
            if int(content_length) > MAX_SAVE_REQUEST_BYTES:
                return HttpResponse("The save request is too large.", status=413)
        except ValueError:
            return HttpResponse("The save request is malformed.", status=400)

    form = SceneSaveForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "scenes/editor.html",
            {"scene": scene, "current_revision": scene.current_revision, "form": form},
            status=422,
        )

    workspace = resolve_owner_workspace(request.user)
    try:
        result = save_scene_content(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            expected_current_revision_id=form.cleaned_data["expected_current_revision_id"],
            expected_scene_version=form.cleaned_data["expected_scene_version"],
            proposed_content=form.cleaned_data["content"],
            idempotency_key=form.cleaned_data["idempotency_key"],
            save_intent=form.cleaned_data["save_intent"],
        )
    except IdempotencyKeyConflict:
        return _render_conflict(
            request,
            scene_id=scene.id,
            submitted_content=form.cleaned_data["content"],
            message="This save request identifier was already used for different changes.",
        )
    except SceneDomainError:
        raise Http404("Scene is unavailable.") from None

    if result.outcome == SaveRequestOutcome.CONFLICTED:
        return _render_conflict(
            request,
            scene_id=scene.id,
            submitted_content=form.cleaned_data["content"],
            message="The Scene changed after this editor was loaded. No changes were saved.",
        )
    return _see_other(reverse("scene-editor", kwargs={"scene_id": result.scene.id}))


def _render_conflict(
    request: HttpRequest,
    *,
    scene_id: uuid.UUID,
    submitted_content: str,
    message: str,
) -> HttpResponse:
    scene = _authorized_scene(request, scene_id)
    if scene.lifecycle != Scene.Lifecycle.ACTIVE:
        raise Http404("Scene is unavailable.")
    current = scene.current_revision
    if current is None:
        raise Http404("Scene is unavailable.")
    reconciliation_form = SceneSaveForm(
        initial={
            "content": submitted_content,
            "expected_current_revision_id": current.id,
            "expected_scene_version": scene.version,
            "idempotency_key": uuid.uuid4().hex,
            "save_intent": "explicit_save",
        }
    )
    return render(
        request,
        "scenes/conflict.html",
        {
            "scene": scene,
            "current_revision": current,
            "current_content": current.content,
            "form": reconciliation_form,
            "conflict_message": message,
        },
        status=409,
    )
