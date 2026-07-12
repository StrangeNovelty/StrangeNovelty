from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from django.test import RequestFactory, override_settings

from accounts.crypto import decrypt_secret, encrypt_secret
from accounts.middleware import MfaAssuranceMiddleware
from accounts.models import (
    AuthenticationChallenge,
    AuthenticationThrottle,
    RecoveryCode,
    RecoveryEnrollment,
    SessionAssurance,
    TOTPCredential,
    WebAuthnCredential,
)
from operations.readiness import mfa_configuration_ready

ROOT = Path(__file__).parents[1]


def test_authentication_schema_excludes_plaintext_secrets_and_raw_sessions() -> None:
    assert WebAuthnCredential._meta.pk.get_internal_type() == "UUIDField"
    assert TOTPCredential._meta.pk.get_internal_type() == "UUIDField"
    assert RecoveryCode._meta.pk.get_internal_type() == "UUIDField"
    assert SessionAssurance._meta.pk.get_internal_type() == "UUIDField"
    assert AuthenticationChallenge._meta.pk.get_internal_type() == "UUIDField"
    assert AuthenticationThrottle._meta.pk.get_internal_type() == "UUIDField"
    assert RecoveryEnrollment._meta.pk.get_internal_type() == "UUIDField"
    names = {
        field.name
        for model in (TOTPCredential, RecoveryCode, SessionAssurance)
        for field in model._meta.fields
    }
    assert "secret" not in names
    assert "code" not in names
    assert "session_key" not in names
    assert "encrypted_secret" in names and "code_hash" in names and "session_digest" in names


def test_fernet_boundary_encrypts_and_detects_wrong_key() -> None:
    key = Fernet.generate_key().decode()
    with override_settings(MFA_ENCRYPTION_KEY=key):
        ciphertext = encrypt_secret(b"synthetic-auth-material")
        assert b"synthetic-auth-material" not in ciphertext
        assert decrypt_secret(ciphertext) == b"synthetic-auth-material"
    with (
        override_settings(MFA_ENCRYPTION_KEY=Fernet.generate_key().decode()),
        pytest.raises(PermissionError),
    ):
        decrypt_secret(ciphertext)


@override_settings(
    MFA_ENFORCED=True,
    MFA_ENCRYPTION_KEY="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
    WEBAUTHN_RP_ID="novel.example",
    WEBAUTHN_ORIGIN="https://novel.example",
)
def test_static_mfa_readiness_configuration_passes() -> None:
    assert mfa_configuration_ready()


@override_settings(MFA_ENFORCED=False)
def test_static_mfa_readiness_fails_closed() -> None:
    assert not mfa_configuration_ready()


def test_mfa_middleware_allows_health_without_database() -> None:
    request = RequestFactory().get("/health/live/")
    request.user = type("User", (), {"is_authenticated": True})()
    response = MfaAssuranceMiddleware(lambda _request: "allowed")(request)
    assert response == "allowed"


def test_webauthn_browser_code_is_local_and_dependency_free() -> None:
    source = (ROOT / "src/accounts/static/accounts/webauthn.js").read_text()
    assert "navigator.credentials" in source
    assert "https://" not in source
    assert "localStorage" not in source


def test_portable_archive_does_not_include_authentication_models() -> None:
    archive_source = (ROOT / "src/archives/services.py").read_text()
    for forbidden in (
        "WebAuthnCredential",
        "TOTPCredential",
        "RecoveryCode",
        "SessionAssurance",
        "AuthenticationChallenge",
    ):
        assert forbidden not in archive_source


def test_scope_has_no_disallowed_authentication_mechanisms() -> None:
    sources = "\n".join(
        path.read_text()
        for path in (ROOT / "src/accounts").rglob("*.py")
        if "migrations" not in path.parts
    ).casefold()
    for forbidden in ("sms", "remember_device", "trusted_device", "social login", "redis"):
        assert forbidden not in sources
