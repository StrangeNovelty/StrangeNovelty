from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import timedelta

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import AuthenticatorSelectionCriteria, UserVerificationRequirement

from accounts.assurance import session_digest
from accounts.crypto import decrypt_secret, encrypt_secret
from accounts.models import (
    Account,
    AuthenticationChallenge,
    RecoveryCode,
    TOTPCredential,
    WebAuthnCredential,
)


def _challenge(
    account: Account, session_key: str, purpose: str, raw: bytes
) -> AuthenticationChallenge:
    AuthenticationChallenge.objects.filter(
        account=account, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=timezone.now())
    return AuthenticationChallenge.objects.create(  # type: ignore[no-any-return]
        account=account,
        session_digest=session_digest(session_key),
        purpose=purpose,
        encrypted_challenge=encrypt_secret(raw),
        expires_at=timezone.now() + timedelta(seconds=settings.WEBAUTHN_CHALLENGE_SECONDS),
    )


def registration_options(account: Account, session_key: str) -> str:
    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=account.id.bytes,
        user_name=account.email,
        user_display_name="Owner",
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.REQUIRED
        ),
    )
    record = _challenge(
        account,
        session_key,
        str(AuthenticationChallenge.Purpose.WEBAUTHN_REGISTER),
        options.challenge,
    )
    payload = json.loads(options_to_json(options))
    payload["challengeRecord"] = str(record.id)
    return json.dumps(payload, separators=(",", ":"))


def _consume_challenge(
    account: Account, session_key: str, challenge_id: uuid.UUID, purpose: str
) -> bytes:
    with transaction.atomic():
        row = AuthenticationChallenge.objects.select_for_update().get(
            id=challenge_id,
            account=account,
            session_digest=session_digest(session_key),
            purpose=purpose,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        row.consumed_at = timezone.now()
        row.save(update_fields=("consumed_at",))
        return decrypt_secret(bytes(row.encrypted_challenge))


def complete_registration(
    account: Account, session_key: str, challenge_id: uuid.UUID, credential: dict, label: str
) -> WebAuthnCredential:
    expected = _consume_challenge(
        account,
        session_key,
        challenge_id,
        str(AuthenticationChallenge.Purpose.WEBAUTHN_REGISTER),
    )
    result = verify_registration_response(
        credential=credential,
        expected_challenge=expected,
        expected_rp_id=settings.WEBAUTHN_RP_ID,
        expected_origin=settings.WEBAUTHN_ORIGIN,
        require_user_verification=True,
    )
    return WebAuthnCredential.objects.create(  # type: ignore[no-any-return]
        account=account,
        credential_id=result.credential_id,
        public_key=result.credential_public_key,
        sign_count=result.sign_count,
        device_type=str(result.credential_device_type.value),
        backed_up=result.credential_backed_up,
        user_verified=result.user_verified,
        label=label.strip()[:80] or "Security key",
    )


def authentication_options(account: Account, session_key: str) -> str:
    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    record = _challenge(
        account,
        session_key,
        str(AuthenticationChallenge.Purpose.WEBAUTHN_AUTHENTICATE),
        options.challenge,
    )
    payload = json.loads(options_to_json(options))
    payload["challengeRecord"] = str(record.id)
    return json.dumps(payload, separators=(",", ":"))


@transaction.atomic
def complete_authentication(
    account: Account, session_key: str, challenge_id: uuid.UUID, credential: dict
) -> WebAuthnCredential:
    expected = _consume_challenge(
        account,
        session_key,
        challenge_id,
        str(AuthenticationChallenge.Purpose.WEBAUTHN_AUTHENTICATE),
    )
    raw_id = credential.get("rawId") or credential.get("id")
    import base64

    padded = str(raw_id) + "=" * (-len(str(raw_id)) % 4)
    credential_id = base64.urlsafe_b64decode(padded)
    stored = WebAuthnCredential.objects.select_for_update().get(
        account=account, credential_id=credential_id, state=WebAuthnCredential.State.ACTIVE
    )
    result = verify_authentication_response(
        credential=credential,
        expected_challenge=expected,
        expected_rp_id=settings.WEBAUTHN_RP_ID,
        expected_origin=settings.WEBAUTHN_ORIGIN,
        credential_public_key=bytes(stored.public_key),
        credential_current_sign_count=stored.sign_count,
        require_user_verification=True,
    )
    if stored.sign_count and result.new_sign_count and result.new_sign_count <= stored.sign_count:
        raise PermissionError("Authenticator verification failed.")
    stored.sign_count = result.new_sign_count
    stored.last_used_at = timezone.now()
    stored.save(update_fields=("sign_count", "last_used_at"))
    return stored  # type: ignore[no-any-return]


def create_pending_totp(account: Account, label: str) -> tuple[TOTPCredential, str]:
    secret = pyotp.random_base32()
    credential = TOTPCredential.objects.create(
        account=account,
        encrypted_secret=encrypt_secret(secret.encode()),
        label=label[:80],
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    return credential, secret


@transaction.atomic
def verify_totp(account: Account, code: str, pending_id: uuid.UUID | None = None) -> TOTPCredential:
    query = TOTPCredential.objects.select_for_update().filter(account=account)
    credential = (
        query.get(id=pending_id, state=TOTPCredential.State.PENDING, expires_at__gt=timezone.now())
        if pending_id
        else query.get(state=TOTPCredential.State.ACTIVE)
    )
    secret = decrypt_secret(bytes(credential.encrypted_secret)).decode()
    totp = pyotp.TOTP(secret, digits=6, interval=30, digest=hashlib.sha1)
    counter = int(timezone.now().timestamp()) // 30
    if not totp.verify(code, valid_window=1) or (
        credential.last_used_counter is not None and counter <= credential.last_used_counter
    ):
        raise PermissionError("Unable to verify authentication code.")
    credential.last_used_counter = counter
    credential.last_used_at = timezone.now()
    if pending_id:
        credential.state = TOTPCredential.State.ACTIVE
        credential.expires_at = None
    credential.save()
    return credential  # type: ignore[no-any-return]


@transaction.atomic
def regenerate_recovery_codes(account: Account, count: int = 10) -> list[str]:
    now, generation = timezone.now(), uuid.uuid4()
    RecoveryCode.objects.filter(
        account=account, used_at__isnull=True, revoked_at__isnull=True
    ).update(revoked_at=now)
    values = [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(count)]
    RecoveryCode.objects.bulk_create(
        [
            RecoveryCode(account=account, generation_id=generation, code_hash=make_password(value))
            for value in values
        ]
    )
    return values


@transaction.atomic
def consume_recovery_code(account: Account, value: str) -> RecoveryCode:
    for row in RecoveryCode.objects.select_for_update().filter(
        account=account, used_at__isnull=True, revoked_at__isnull=True
    ):
        if check_password(value, row.code_hash):
            row.used_at = timezone.now()
            row.save(update_fields=("used_at",))
            return row  # type: ignore[no-any-return]
    raise PermissionError("Unable to verify recovery code.")
