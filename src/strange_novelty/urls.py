"""Root URL configuration with no private application routes yet."""

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path

from accounts.views import WorkspaceLoginView, WorkspaceLogoutView
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
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
