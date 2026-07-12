from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from accounts.assurance import is_mfa_assured


class MfaAssuranceMiddleware:
    ALLOWED_PREFIXES = ("/login/", "/logout/", "/mfa/", "/account/security/", "/health/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if (
            settings.MFA_ENFORCED
            and request.user.is_authenticated
            and not request.path.startswith(self.ALLOWED_PREFIXES)
            and not is_mfa_assured(request)
        ):
            return redirect("mfa-challenge")
        return self.get_response(request)
