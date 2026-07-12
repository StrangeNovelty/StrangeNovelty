from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from security_events.services import new_correlation_id, validated_correlation_id


class RequestCorrelationMiddleware:
    header_name = "X-Request-ID"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = new_correlation_id()
        request.correlation_id = correlation_id
        response = self.get_response(request)
        response.headers[self.header_name] = correlation_id
        return response


def request_correlation_id(request: HttpRequest) -> str:
    candidate = getattr(request, "correlation_id", None)
    return validated_correlation_id(candidate)
