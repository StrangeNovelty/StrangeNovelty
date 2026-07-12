import json
import uuid
from typing import cast

from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.assurance import (
    current_assurance,
    establish_password_assurance,
    is_mfa_assured,
    is_recent,
    revoke_assurance,
    session_digest,
    upgrade_assurance,
)
from accounts.forms import (
    AccountPasswordChangeForm,
    EmailAuthenticationForm,
    MfaCodeForm,
    RecoveryCodeForm,
    TotpEnrollmentForm,
)
from accounts.mfa import (
    authentication_options,
    complete_authentication,
    complete_registration,
    consume_recovery_code,
    create_pending_totp,
    regenerate_recovery_codes,
    registration_options,
    verify_totp,
)
from accounts.models import (
    Account,
    RecoveryEnrollment,
    SessionAssurance,
    TOTPCredential,
    WebAuthnCredential,
)
from accounts.throttling import clear_failures, is_blocked, register_failure
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
        clear_failures("password", f"login:{actor.email.casefold()}")
        establish_password_assurance(self.request, actor)
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
        if settings.MFA_ENFORCED:
            self.request.session["mfa_next"] = response.headers.get("Location", "/workspace/")
            return redirect("mfa-challenge")
        return response

    def form_invalid(self, form: EmailAuthenticationForm) -> HttpResponse:
        attempted = self.request.POST.get("username", "").strip().casefold()
        register_failure("password", f"login:{attempted}")
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
            assurance = current_assurance(request)
            if assurance:
                assurance.revoked_at = timezone.now()
                assurance.revocation_reason = "logout"
                assurance.save(update_fields=("revoked_at", "revocation_reason"))
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


def _record_mfa_event(
    request: HttpRequest,
    event_type: SecurityEventType,
    outcome: SecurityOutcome = SecurityOutcome.SUCCEEDED,
    reason: SecurityReason = SecurityReason.NONE,
) -> None:
    actor = cast(Account, request.user)
    record_security_event(
        SecurityEventSpec(
            event_type=event_type,
            outcome=outcome,
            actor=actor,
            target_category=SecurityTargetCategory.MFA_FACTOR,
            target_id=actor.id,
            correlation_id=request_correlation_id(request),
            service_role=SecurityServiceRole.WEB,
            reason=reason,
        )
    )


def _require_owner(request: HttpRequest) -> Workspace:
    return resolve_owner_workspace(cast(Account, request.user))


def _mfa_scope(request: HttpRequest) -> str:
    return f"account:{request.user.id}"


def _post_mfa_destination(request: HttpRequest) -> str:
    return str(request.session.pop("mfa_next", "/workspace/"))


def _sensitive_ready(request: HttpRequest) -> bool:
    has_factor = (
        WebAuthnCredential.objects.filter(
            account=request.user, state=WebAuthnCredential.State.ACTIVE
        ).exists()
        or TOTPCredential.objects.filter(
            account=request.user, state=TOTPCredential.State.ACTIVE
        ).exists()
    )
    recovery = RecoveryEnrollment.objects.filter(
        account=request.user,
        used_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).exists()
    return bool(is_recent(request) and (not has_factor or is_mfa_assured(request) or recovery))


@never_cache
@login_required
def mfa_challenge(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    if current_assurance(request) is None:
        establish_password_assurance(request, cast(Account, request.user))
    blocked = is_blocked("totp", _mfa_scope(request))
    if request.method == "POST":
        form = MfaCodeForm(request.POST)
        if form.is_valid() and not blocked:
            try:
                verify_totp(cast(Account, request.user), form.cleaned_data["code"])
                upgrade_assurance(request, SessionAssurance.Method.TOTP)
                clear_failures("totp", _mfa_scope(request))
                _record_mfa_event(request, SecurityEventType.MFA_SUCCEEDED)
                return redirect(_post_mfa_destination(request))
            except PermissionError, TOTPCredential.DoesNotExist:
                register_failure("totp", _mfa_scope(request))
                _record_mfa_event(
                    request,
                    SecurityEventType.MFA_FAILED,
                    SecurityOutcome.DENIED,
                    SecurityReason.INVALID_MFA,
                )
                form.add_error("code", "Unable to verify authentication code.")
    else:
        form = MfaCodeForm()
    return render(
        request,
        "accounts/mfa_challenge.html",
        {
            "form": form,
            "has_totp": TOTPCredential.objects.filter(
                account=request.user, state=TOTPCredential.State.ACTIVE
            ).exists(),
        },
    )


@require_POST
@login_required
def webauthn_auth_options(request: HttpRequest) -> JsonResponse:
    _require_owner(request)
    return JsonResponse(
        json.loads(
            authentication_options(cast(Account, request.user), request.session.session_key or "")
        )
    )


@require_POST
@login_required
def webauthn_auth_complete(request: HttpRequest) -> JsonResponse:
    _require_owner(request)
    if is_blocked("webauthn", _mfa_scope(request)):
        return JsonResponse({"outcome": "denied"}, status=400)
    try:
        payload = json.loads(request.body)
        complete_authentication(
            cast(Account, request.user),
            request.session.session_key or "",
            uuid.UUID(payload.pop("challengeRecord")),
            payload,
        )
        upgrade_assurance(request, SessionAssurance.Method.WEBAUTHN)
        clear_failures("webauthn", _mfa_scope(request))
        _record_mfa_event(request, SecurityEventType.MFA_SUCCEEDED)
        return JsonResponse({"outcome": "succeeded", "redirect": _post_mfa_destination(request)})
    except ValueError, KeyError, PermissionError, WebAuthnCredential.DoesNotExist:
        register_failure("webauthn", _mfa_scope(request))
        return JsonResponse({"outcome": "denied"}, status=400)


@never_cache
@login_required
def security_home(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    assurance = current_assurance(request)
    sessions = SessionAssurance.objects.filter(
        account=request.user, revoked_at__isnull=True
    ).order_by("-created_at")
    return render(
        request,
        "accounts/security.html",
        {
            "assurance": assurance,
            "sessions": sessions,
            "webauthn": WebAuthnCredential.objects.filter(
                account=request.user, state=WebAuthnCredential.State.ACTIVE
            ),
            "totp": TOTPCredential.objects.filter(
                account=request.user, state=TOTPCredential.State.ACTIVE
            ),
        },
    )


@require_POST
@login_required
def webauthn_register_options(request: HttpRequest) -> JsonResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return JsonResponse({"outcome": "recent_authentication_required"}, status=403)
    return JsonResponse(
        json.loads(
            registration_options(cast(Account, request.user), request.session.session_key or "")
        )
    )


@require_POST
@login_required
def webauthn_register_complete(request: HttpRequest) -> JsonResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return JsonResponse({"outcome": "denied"}, status=403)
    try:
        payload = json.loads(request.body)
        challenge_id = uuid.UUID(payload.pop("challengeRecord"))
        label = str(payload.pop("label", "Security key"))
        complete_registration(
            cast(Account, request.user),
            request.session.session_key or "",
            challenge_id,
            payload,
            label,
        )
        RecoveryEnrollment.objects.filter(
            account=request.user,
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).update(used_at=timezone.now())
        _record_mfa_event(request, SecurityEventType.WEBAUTHN_ENROLLED)
        return JsonResponse({"outcome": "succeeded"})
    except ValueError, KeyError, PermissionError:
        return JsonResponse({"outcome": "denied"}, status=400)


@never_cache
@login_required
def totp_enroll(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return HttpResponse("Recent authentication required.", status=403)
    secret = None
    if request.method == "POST":
        form = TotpEnrollmentForm(request.POST)
        if form.is_valid():
            credential, secret = create_pending_totp(
                cast(Account, request.user), form.cleaned_data["label"]
            )
            request.session["pending_totp_id"] = str(credential.id)
    else:
        form = TotpEnrollmentForm()
    return render(
        request,
        "accounts/totp_enroll.html",
        {"form": form, "secret": secret, "confirm_form": MfaCodeForm()},
    )


@require_POST
@login_required
def totp_confirm(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    form = MfaCodeForm(request.POST)
    try:
        if not form.is_valid():
            raise PermissionError
        verify_totp(
            cast(Account, request.user),
            form.cleaned_data["code"],
            uuid.UUID(request.session.pop("pending_totp_id")),
        )
        _record_mfa_event(request, SecurityEventType.TOTP_ENROLLED)
        return redirect("account-security")
    except PermissionError, KeyError, ValueError, TOTPCredential.DoesNotExist:
        return HttpResponse("Unable to confirm authenticator.", status=400)


@require_POST
@login_required
def webauthn_revoke(request: HttpRequest, credential_id: uuid.UUID) -> HttpResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return HttpResponse("Recent authentication required.", status=403)
    credential = WebAuthnCredential.objects.filter(
        id=credential_id, account=request.user, state=WebAuthnCredential.State.ACTIVE
    ).first()
    if credential is None:
        raise Http404
    credential.state = WebAuthnCredential.State.REVOKED
    credential.revoked_at = timezone.now()
    credential.save(update_fields=("state", "revoked_at"))
    _record_mfa_event(request, SecurityEventType.WEBAUTHN_REVOKED)
    return redirect("account-security")


@require_POST
@login_required
def totp_revoke(request: HttpRequest, credential_id: uuid.UUID) -> HttpResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return HttpResponse("Recent authentication required.", status=403)
    credential = TOTPCredential.objects.filter(
        id=credential_id, account=request.user, state=TOTPCredential.State.ACTIVE
    ).first()
    if credential is None:
        raise Http404
    credential.state = TOTPCredential.State.REVOKED
    credential.revoked_at = timezone.now()
    credential.save(update_fields=("state", "revoked_at"))
    _record_mfa_event(request, SecurityEventType.TOTP_REVOKED)
    return redirect("account-security")


@require_POST
@login_required
def recovery_codes_regenerate(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    if not _sensitive_ready(request) or not (
        WebAuthnCredential.objects.filter(
            account=request.user, state=WebAuthnCredential.State.ACTIVE
        ).exists()
        or TOTPCredential.objects.filter(
            account=request.user, state=TOTPCredential.State.ACTIVE
        ).exists()
    ):
        return HttpResponse("Recent authentication and an active factor are required.", status=403)
    codes = regenerate_recovery_codes(cast(Account, request.user))
    _record_mfa_event(request, SecurityEventType.RECOVERY_CODES_GENERATED)
    return render(
        request,
        "accounts/recovery_codes.html",
        {"codes": codes},
    )


@require_POST
@login_required
def recovery_code_verify(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    if is_blocked("recovery", _mfa_scope(request)):
        return HttpResponse("Unable to verify recovery code.", status=400)
    form = RecoveryCodeForm(request.POST)
    try:
        if not form.is_valid():
            raise PermissionError
        consume_recovery_code(cast(Account, request.user), form.cleaned_data["code"])
        upgrade_assurance(request, SessionAssurance.Method.RECOVERY_CODE)
        clear_failures("recovery", _mfa_scope(request))
        _record_mfa_event(request, SecurityEventType.RECOVERY_CODE_USED)
        return redirect(_post_mfa_destination(request))
    except PermissionError:
        register_failure("recovery", _mfa_scope(request))
        return render(
            request,
            "accounts/mfa_challenge.html",
            {"form": MfaCodeForm(), "recovery_form": form},
            status=400,
        )


@require_POST
@login_required
def revoke_session(request: HttpRequest, assurance_id: uuid.UUID) -> HttpResponse:
    _require_owner(request)
    target = SessionAssurance.objects.filter(id=assurance_id, account=request.user).first()
    if target is None:
        raise Http404
    if target != current_assurance(request) and not _sensitive_ready(request):
        return HttpResponse("Recent authentication required.", status=403)
    revoke_assurance(target, "owner_revoked")
    _record_mfa_event(request, SecurityEventType.SESSION_REVOKED)
    return redirect("login" if target == current_assurance(request) else "account-security")


@require_POST
@login_required
def revoke_other_sessions(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return HttpResponse("Recent authentication required.", status=403)
    current = current_assurance(request)
    for assurance in SessionAssurance.objects.filter(
        account=request.user, revoked_at__isnull=True
    ).exclude(id=current.id if current else None):
        revoke_assurance(assurance, "owner_revoked")
    _record_mfa_event(request, SecurityEventType.SESSION_REVOKED)
    return redirect("account-security")


@never_cache
@login_required
def password_change(request: HttpRequest) -> HttpResponse:
    _require_owner(request)
    if not _sensitive_ready(request):
        return HttpResponse("Recent authentication required.", status=403)
    form = AccountPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        current = current_assurance(request)
        for assurance in SessionAssurance.objects.filter(
            account=user, revoked_at__isnull=True
        ).exclude(id=current.id if current else None):
            revoke_assurance(assurance, "password_changed")
        update_session_auth_hash(request, user)
        if current is not None:
            current.session_digest = session_digest(request.session.session_key or "")
            current.password_authenticated_at = timezone.now()
            current.recent_authenticated_at = timezone.now()
            current.save(
                update_fields=(
                    "session_digest",
                    "password_authenticated_at",
                    "recent_authenticated_at",
                )
            )
        _record_mfa_event(request, SecurityEventType.PASSWORD_CHANGED)
        return redirect("account-security")
    return render(request, "accounts/password_change.html", {"form": form})
