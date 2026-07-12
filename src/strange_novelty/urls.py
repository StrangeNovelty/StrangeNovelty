"""Root URL configuration with no private application routes yet."""

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path

from accounts.views import WorkspaceLoginView, WorkspaceLogoutView
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
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
