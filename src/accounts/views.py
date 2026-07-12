from typing import cast

from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404, HttpRequest, HttpResponse

from accounts.forms import EmailAuthenticationForm
from accounts.models import Account
from security_events.middleware import request_correlation_id
from security_events.services import SecurityEventSpec, record_security_event
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)
from workspaces.models import Workspace
from workspaces.services import resolve_owner_workspace


class WorkspaceLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = False
    next_page = "workspace-home"

    def form_valid(self, form: EmailAuthenticationForm) -> HttpResponse:
        response = super().form_valid(form)
        actor = cast(Account, form.get_user())
        workspace: Workspace | None
        try:
            workspace = resolve_owner_workspace(actor)
        except Http404:
            workspace = None
        record_security_event(
            SecurityEventSpec(
                event_type=SecurityEventType.LOGIN_SUCCEEDED,
                outcome=SecurityOutcome.SUCCEEDED,
                actor=actor,
                workspace=workspace,
                target_category=SecurityTargetCategory.AUTHENTICATION,
                target_id=actor.id,
                correlation_id=request_correlation_id(self.request),
                service_role=SecurityServiceRole.WEB,
            )
        )
        return response

    def form_invalid(self, form: EmailAuthenticationForm) -> HttpResponse:
        record_security_event(
            SecurityEventSpec(
                event_type=SecurityEventType.LOGIN_FAILED,
                outcome=SecurityOutcome.DENIED,
                target_category=SecurityTargetCategory.AUTHENTICATION,
                correlation_id=request_correlation_id(self.request),
                service_role=SecurityServiceRole.WEB,
                reason=SecurityReason.INVALID_CREDENTIALS,
            )
        )
        return super().form_invalid(form)


class WorkspaceLogoutView(LogoutView):
    next_page = "login"

    def post(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        actor = cast(Account, request.user) if request.user.is_authenticated else None
        if actor is not None:
            try:
                workspace = resolve_owner_workspace(actor)
            except Http404:
                workspace = None
        else:
            workspace = None
        response = super().post(request, *args, **kwargs)
        if actor is not None:
            record_security_event(
                SecurityEventSpec(
                    event_type=SecurityEventType.LOGOUT_SUCCEEDED,
                    outcome=SecurityOutcome.SUCCEEDED,
                    actor=actor,
                    workspace=workspace,
                    target_category=SecurityTargetCategory.SESSION,
                    correlation_id=request_correlation_id(request),
                    service_role=SecurityServiceRole.WEB,
                )
            )
        return response
