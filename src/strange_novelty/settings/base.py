"""Settings shared by all Strange Novelty environments."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

SECRET_KEY = ""
DEBUG = False
ALLOWED_HOSTS: list[str] = []
AI_ENABLED = False
AI_ADAPTER = "disabled"
AI_OPENROUTER_API_KEY = ""
AI_MODEL = ""
AI_TIMEOUT_SECONDS = 45
AI_MAX_OUTPUT_TOKENS = 4000
MAINTENANCE_MODE = False
MFA_ENFORCED = False
MFA_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
WEBAUTHN_RP_ID = "localhost"
WEBAUTHN_ORIGIN = "http://localhost:8000"
WEBAUTHN_RP_NAME = "Strange Novelty"
WEBAUTHN_CHALLENGE_SECONDS = 300
MFA_RECENT_AUTH_SECONDS = 300
MFA_SESSION_MAX_AGE_SECONDS = 43200
AUTH_THROTTLE_WINDOW_SECONDS = 600
AUTH_THROTTLE_MAX_ATTEMPTS = 5
AUTH_THROTTLE_BLOCK_SECONDS = 900
SERVICE_ROLE = "development"
RELEASE_VERSION = "development"
SOURCE_COMMIT = "development"
BUILD_IDENTIFIER = "development"
CONFIGURATION_SCHEMA_VERSION = "config-v1"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "accounts.apps.AccountsConfig",
    "workspaces.apps.WorkspacesConfig",
    "scenes.apps.ScenesConfig",
    "characters.apps.CharactersConfig",
    "stories.apps.StoriesConfig",
    "worldbuilding.apps.WorldbuildingConfig",
    "decks.apps.DecksConfig",
    "continuity.apps.ContinuityConfig",
    "timeline.apps.TimelineConfig",
    "security_events.apps.SecurityEventsConfig",
    "jobs.apps.JobsConfig",
    "archives.apps.ArchivesConfig",
    "legacy_imports.apps.LegacyImportsConfig",
    "ai_assistance.apps.AiAssistanceConfig",
    "library.apps.LibraryConfig",
    "publishing.apps.PublishingConfig",
    "operations.apps.OperationsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "security_events.middleware.RequestCorrelationMiddleware",
    "operations.middleware.OperationalRequestLogMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.MfaAssuranceMiddleware",
    "operations.middleware.MaintenanceModeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "strange_novelty.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "strange_novelty.wsgi.application"
ASGI_APPLICATION = "strange_novelty.asgi.application"

DATABASES: dict[str, dict[str, object]] = {}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.Account"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "workspace-home"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
MEDIA_ROOT = Path(os.environ.get("PRIVATE_MEDIA_ROOT", BASE_DIR / ".private-media"))
LIBRARY_MAX_UPLOAD_BYTES = int(os.environ.get("LIBRARY_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
LIBRARY_MAX_EXTRACT_BYTES = int(os.environ.get("LIBRARY_MAX_EXTRACT_BYTES", str(10 * 1024 * 1024)))
LIBRARY_MAX_EXTRACTED_TEXT_CHARS = int(
    os.environ.get("LIBRARY_MAX_EXTRACTED_TEXT_CHARS", "2000000")
)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Optional local-only source-render root used by the authenticated review interface.
DECK_AUDIT_ROOT = ""

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = False

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
