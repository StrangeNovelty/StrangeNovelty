"""Root URL configuration with no private application routes yet."""

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path

from accounts.views import WorkspaceLoginView, WorkspaceLogoutView
from ai_assistance.views import (
    ai_request_status,
    apply_ai_suggestion,
    cancel_ai_request_view,
    expire_ai_suggestion,
    reject_ai_suggestion,
    request_ai_suggestion,
    review_ai_suggestion,
)
from scenes.search_views import scene_search
from scenes.views import scene_create, scene_editor, scene_list, scene_save
from workspaces.views import root, workspace_home


def health(request: HttpRequest) -> HttpResponse:
    """Return a bounded process-level response without internal details."""
    del request
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("", root, name="root"),
    path("login/", WorkspaceLoginView.as_view(), name="login"),
    path("logout/", WorkspaceLogoutView.as_view(), name="logout"),
    path("workspace/", workspace_home, name="workspace-home"),
    path("scenes/", scene_list, name="scene-list"),
    path("scenes/new/", scene_create, name="scene-create"),
    path("scenes/<uuid:scene_id>/", scene_editor, name="scene-editor"),
    path("scenes/<uuid:scene_id>/save/", scene_save, name="scene-save"),
    path("scenes/<uuid:scene_id>/ai/request/", request_ai_suggestion, name="ai-request"),
    path("ai/requests/<uuid:request_id>/", ai_request_status, name="ai-request-status"),
    path("ai/requests/<uuid:request_id>/cancel/", cancel_ai_request_view, name="ai-request-cancel"),
    path("ai/suggestions/<uuid:suggestion_id>/", review_ai_suggestion, name="ai-suggestion-review"),
    path(
        "ai/suggestions/<uuid:suggestion_id>/apply/",
        apply_ai_suggestion,
        name="ai-suggestion-apply",
    ),
    path(
        "ai/suggestions/<uuid:suggestion_id>/reject/",
        reject_ai_suggestion,
        name="ai-suggestion-reject",
    ),
    path(
        "ai/suggestions/<uuid:suggestion_id>/expire/",
        expire_ai_suggestion,
        name="ai-suggestion-expire",
    ),
    path("search/", scene_search, name="scene-search"),
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
