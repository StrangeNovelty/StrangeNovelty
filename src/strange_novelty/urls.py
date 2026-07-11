"""Root URL configuration with no private application routes yet."""

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path


def health(request: HttpRequest) -> HttpResponse:
    """Return a bounded process-level response without internal details."""
    del request
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
]
