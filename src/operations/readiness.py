import re
from pathlib import Path

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
