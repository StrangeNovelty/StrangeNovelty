import re
from pathlib import Path

from cryptography.fernet import Fernet
from django.conf import settings

RELEASE_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{1,64}$")
REQUIRED_RUNBOOKS = (
    "docs/operations/backup-and-restore-runbook.md",
    "docs/operations/deployment-runbook.md",
    "docs/operations/incident-response-runbook.md",
    "docs/operations/secret-rotation-runbook.md",
    "docs/operations/maintenance-mode-runbook.md",
    "docs/operations/break-glass-runbook.md",
    "docs/operations/production-readiness-checklist.md",
    "docs/operations/account-recovery-runbook.md",
)


def static_readiness_checks(base_dir: Path | None = None) -> dict[str, bool]:
    root = base_dir or settings.BASE_DIR
    return {
        "debug_disabled": settings.DEBUG is False,
        "secure_cookies": settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE,
        "https_required": settings.SECURE_SSL_REDIRECT is True,
        "postgresql_backend": settings.DATABASES["default"]["ENGINE"]
        == "django.db.backends.postgresql",
        "release_identity": all(
            RELEASE_PATTERN.fullmatch(value)
            for value in (
                settings.RELEASE_VERSION,
                settings.SOURCE_COMMIT,
                settings.BUILD_IDENTIFIER,
                settings.CONFIGURATION_SCHEMA_VERSION,
            )
        ),
        "service_role": settings.SERVICE_ROLE in {"web", "worker", "migration"},
        "ai_fake_disabled": not settings.AI_ENABLED and settings.AI_ADAPTER != "local_fake",
        "static_manifest_storage": settings.STORAGES["staticfiles"]["BACKEND"].endswith(
            "CompressedManifestStaticFilesStorage"
        ),
        "runbooks_present": all((root / path).is_file() for path in REQUIRED_RUNBOOKS),
    }


def mfa_configuration_ready() -> bool:
    try:
        Fernet(settings.MFA_ENCRYPTION_KEY.encode("ascii"))
    except ValueError, UnicodeEncodeError, AttributeError:
        return False
    return bool(
        settings.MFA_ENFORCED
        and settings.WEBAUTHN_RP_ID
        and settings.WEBAUTHN_ORIGIN.startswith("https://")
    )


def owner_mfa_ready() -> bool:
    from accounts.models import Account, RecoveryCode, RecoveryEnrollment, WebAuthnCredential
    from workspaces.models import WorkspaceGrant

    owners = Account.objects.filter(
        is_active=True,
        workspace_grants__role=WorkspaceGrant.Role.OWNER,
        workspace_grants__state=WorkspaceGrant.State.ACTIVE,
    ).distinct()
    return any(
        WebAuthnCredential.objects.filter(
            account=owner, state=WebAuthnCredential.State.ACTIVE
        ).exists()
        and RecoveryCode.objects.filter(
            account=owner, used_at__isnull=True, revoked_at__isnull=True
        ).exists()
        and not RecoveryEnrollment.objects.filter(
            account=owner, used_at__isnull=True, revoked_at__isnull=True
        ).exists()
        for owner in owners
    )
