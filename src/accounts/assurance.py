from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.models import (
    Account,
    AuthenticationChallenge,
    RecoveryEnrollment,
    SessionAssurance,
    TOTPCredential,
)


def session_digest(value: str) -> str:
    return salted_hmac(  # type: ignore[no-any-return]
        "accounts.session-assurance", value, secret=settings.SECRET_KEY, algorithm="sha256"
    ).hexdigest()


def current_assurance(request: HttpRequest) -> SessionAssurance | None:
    if not request.user.is_authenticated or not request.session.session_key:
        return None
    return SessionAssurance.objects.filter(  # type: ignore[no-any-return]
        account=request.user,
        session_digest=session_digest(request.session.session_key),
        revoked_at__isnull=True,
    ).first()


def establish_password_assurance(request: HttpRequest, account: Account) -> SessionAssurance:
    if request.session.session_key is None:
        request.session.create()
    now = timezone.now()
    return SessionAssurance.objects.create(  # type: ignore[no-any-return]
        account=account,
        session_digest=session_digest(request.session.session_key or ""),
        password_authenticated_at=now,
        recent_authenticated_at=now,
    )


@transaction.atomic
def upgrade_assurance(request: HttpRequest, method: str) -> SessionAssurance:
    old = current_assurance(request)
    if old is None:
        raise PermissionError("Password assurance is required.")
    now = timezone.now()
    old.revoked_at = now
    old.revocation_reason = "upgraded"
    old.save(update_fields=("revoked_at", "revocation_reason"))
    request.session.cycle_key()
    return SessionAssurance.objects.create(  # type: ignore[no-any-return]
        account=old.account,
        session_digest=session_digest(request.session.session_key or ""),
        password_authenticated_at=old.password_authenticated_at,
        mfa_authenticated_at=now,
        recent_authenticated_at=now,
        assurance_level=SessionAssurance.Level.MFA,
        mfa_method=method,
    )


def is_mfa_assured(request: HttpRequest) -> bool:
    assurance = current_assurance(request)
    if assurance is None or assurance.assurance_level != SessionAssurance.Level.MFA:
        return False
    return bool(
        assurance.created_at
        >= timezone.now() - timedelta(seconds=settings.MFA_SESSION_MAX_AGE_SECONDS)
    )


def is_recent(request: HttpRequest) -> bool:
    assurance = current_assurance(request)
    return bool(
        assurance
        and assurance.recent_authenticated_at
        and assurance.recent_authenticated_at
        >= timezone.now() - timedelta(seconds=settings.MFA_RECENT_AUTH_SECONDS)
    )


@transaction.atomic
def revoke_assurance(assurance: SessionAssurance, reason: str) -> None:
    if assurance.revoked_at:
        return
    assurance.revoked_at = timezone.now()
    assurance.revocation_reason = reason[:24]
    assurance.save(update_fields=("revoked_at", "revocation_reason"))
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session_digest(session.session_key) == assurance.session_digest:
            session.delete()
            break


@transaction.atomic
def invalidate_authentication_state() -> dict[str, int]:
    now = timezone.now()
    sessions, _ = Session.objects.all().delete()
    assurances = SessionAssurance.objects.filter(revoked_at__isnull=True).update(
        revoked_at=now, revocation_reason="restore"
    )
    challenges = AuthenticationChallenge.objects.filter(consumed_at__isnull=True).update(
        consumed_at=now
    )
    enrollments = RecoveryEnrollment.objects.filter(
        used_at__isnull=True, revoked_at__isnull=True
    ).update(revoked_at=now)
    pending_totp = TOTPCredential.objects.filter(state=TOTPCredential.State.PENDING).update(
        state=TOTPCredential.State.REVOKED, revoked_at=now
    )
    return {
        "sessions": sessions,
        "assurances": assurances,
        "challenges": challenges,
        "recovery": enrollments,
        "pending_totp": pending_totp,
    }
