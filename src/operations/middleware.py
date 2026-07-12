import logging
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
RECOVERY_PATHS = {"/login/", "/logout/"}
logger = logging.getLogger("strange_novelty.http")


class OperationalRequestLogMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        status_class = f"{response.status_code // 100}xx"
        logger.info(
            "",
            extra={
                "event": f"http_{status_class}",
                "correlation_id": getattr(request, "correlation_id", ""),
            },
        )
        return response


class MaintenanceModeMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            settings.MAINTENANCE_MODE
            and request.method not in SAFE_METHODS
            and request.path not in RECOVERY_PATHS
            and not request.path.startswith("/health/")
        ):
            return render(request, "operations/maintenance.html", status=503)
        return self.get_response(request)
