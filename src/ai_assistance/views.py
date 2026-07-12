import uuid
from typing import cast

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Account
from ai_assistance.exceptions import AIAssistanceError, AIRequestConflict, StaleSuggestion
from ai_assistance.forms import AIRequestForm, AISuggestionApplyForm
from ai_assistance.models import AIRequest, AISuggestion
from ai_assistance.services import (
    apply_suggestion,
    cancel_ai_request,
    expire_suggestion,
    reject_suggestion,
    request_suggestion,
    suggestion_is_stale,
)
from scenes.models import Scene
from workspaces.models import Workspace
from workspaces.services import resolve_owner_workspace


def _see_other(location: str) -> HttpResponseRedirect:
    response = HttpResponseRedirect(location)
    response.status_code = 303
    return response


def _workspace(request: HttpRequest) -> Workspace:
    try:
        return resolve_owner_workspace(request.user)
    except Http404:
        raise Http404("AI assistance is unavailable.") from None


def _suggestion(request: HttpRequest, suggestion_id: uuid.UUID) -> AISuggestion:
    workspace = _workspace(request)
    try:
        return cast(
            AISuggestion,
            AISuggestion.objects.select_related(
                "scene", "scene__current_revision", "source_revision", "request"
            ).get(id=suggestion_id, workspace=workspace),
        )
    except AISuggestion.DoesNotExist as exc:
        raise Http404("AI Suggestion is unavailable.") from exc


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def request_ai_suggestion(request: HttpRequest, scene_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    try:
        scene = cast(
            Scene,
            Scene.objects.select_related("current_revision").get(
                id=scene_id, workspace=workspace, lifecycle=Scene.Lifecycle.ACTIVE
            ),
        )
    except Scene.DoesNotExist as exc:
        raise Http404("Scene is unavailable.") from exc
    form = AIRequestForm(request.POST or None, initial={"idempotency_key": uuid.uuid4().hex})
    if request.method == "POST" and form.is_valid():
        try:
            result = request_suggestion(
                account=cast(Account, request.user),
                scene_id=scene.id,
                instruction=form.cleaned_data["instruction"],
                idempotency_key=form.cleaned_data["idempotency_key"],
            )
        except AIRequestConflict:
            form.add_error(None, "This request identifier was already used differently.")
        except AIAssistanceError:
            form.add_error(None, "The AI request could not be created.")
        else:
            return _see_other(
                reverse("ai-request-status", kwargs={"request_id": result.request.id})
            )
    return render(
        request,
        "ai_assistance/request.html",
        {"scene": scene, "source_revision": scene.current_revision, "form": form},
        status=409 if form.non_field_errors() else (422 if request.method == "POST" else 200),
    )


@never_cache
@login_required
@require_http_methods(["GET"])
def ai_request_status(request: HttpRequest, request_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    try:
        ai_request = cast(
            AIRequest,
            AIRequest.objects.select_related("scene").get(id=request_id, workspace=workspace),
        )
    except AIRequest.DoesNotExist as exc:
        raise Http404("AI Request is unavailable.") from exc
    suggestion = AISuggestion.objects.filter(request=ai_request).first()
    return render(
        request,
        "ai_assistance/request_status.html",
        {"ai_request": ai_request, "suggestion": suggestion},
    )


@never_cache
@login_required
@require_POST
def cancel_ai_request_view(request: HttpRequest, request_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    try:
        ai_request = cast(AIRequest, AIRequest.objects.get(id=request_id, workspace=workspace))
        cancel_ai_request(account=cast(Account, request.user), request_id=ai_request.id)
    except AIRequest.DoesNotExist, AIAssistanceError:
        raise Http404("AI Request is unavailable.") from None
    return _see_other(reverse("ai-request-status", kwargs={"request_id": ai_request.id}))


@never_cache
@login_required
@require_http_methods(["GET"])
def review_ai_suggestion(request: HttpRequest, suggestion_id: uuid.UUID) -> HttpResponse:
    suggestion = _suggestion(request, suggestion_id)
    stale = suggestion_is_stale(suggestion)
    form = AISuggestionApplyForm(
        initial={"review_text": suggestion.review_text, "idempotency_key": uuid.uuid4().hex}
    )
    return render(
        request,
        "ai_assistance/review.html",
        {"suggestion": suggestion, "stale": stale, "form": form},
    )


@never_cache
@login_required
@require_POST
def apply_ai_suggestion(request: HttpRequest, suggestion_id: uuid.UUID) -> HttpResponse:
    suggestion = _suggestion(request, suggestion_id)
    form = AISuggestionApplyForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "ai_assistance/review.html",
            {"suggestion": suggestion, "stale": suggestion_is_stale(suggestion), "form": form},
            status=422,
        )
    try:
        applied = apply_suggestion(
            account=cast(Account, request.user),
            suggestion_id=suggestion.id,
            review_text=form.cleaned_data["review_text"],
            idempotency_key=form.cleaned_data["idempotency_key"],
        )
    except StaleSuggestion:
        return render(
            request,
            "ai_assistance/review.html",
            {"suggestion": _suggestion(request, suggestion.id), "stale": True, "form": form},
            status=409,
        )
    except AIAssistanceError:
        raise Http404("AI Suggestion is unavailable.") from None
    return _see_other(reverse("scene-editor", kwargs={"scene_id": applied.scene_id}))


@never_cache
@login_required
@require_POST
def reject_ai_suggestion(request: HttpRequest, suggestion_id: uuid.UUID) -> HttpResponse:
    suggestion = _suggestion(request, suggestion_id)
    try:
        reject_suggestion(account=cast(Account, request.user), suggestion_id=suggestion.id)
    except AIAssistanceError:
        raise Http404("AI Suggestion is unavailable.") from None
    return _see_other(reverse("ai-suggestion-review", kwargs={"suggestion_id": suggestion.id}))


@never_cache
@login_required
@require_POST
def expire_ai_suggestion(request: HttpRequest, suggestion_id: uuid.UUID) -> HttpResponse:
    suggestion = _suggestion(request, suggestion_id)
    try:
        expire_suggestion(account=cast(Account, request.user), suggestion_id=suggestion.id)
    except AIAssistanceError:
        raise Http404("AI Suggestion is unavailable.") from None
    return _see_other(reverse("ai-suggestion-review", kwargs={"suggestion_id": suggestion.id}))
