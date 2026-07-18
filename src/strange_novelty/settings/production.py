"""Fail-closed production settings."""

import os

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .environment import parse_bool, parse_csv, parse_int, postgres_database, require_value
from .storage import private_storage_settings

SECRET_KEY = require_value("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("<", "development-", "test-")):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is unsafe for production.")

DEBUG = parse_bool("DJANGO_DEBUG", default=False)
if DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false in production.")

ALLOWED_HOSTS = parse_csv("DJANGO_ALLOWED_HOSTS", required=True)
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Wildcard ALLOWED_HOSTS is prohibited in production.")

DATABASES = {"default": postgres_database(require_value("DATABASE_URL"), require_credentials=True)}
DATABASES["default"].update(
    {
        "CONN_MAX_AGE": parse_int("DATABASE_CONN_MAX_AGE", default=60, minimum=0, maximum=600),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 5,
            "options": "-c statement_timeout=30000 -c lock_timeout=5000",
        },
    }
)

AI_ENABLED = parse_bool("AI_ENABLED", default=False)
AI_ADAPTER = os.environ.get("AI_ADAPTER", "disabled").strip()
AI_OPENROUTER_API_KEY = os.environ.get("AI_OPENROUTER_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "").strip()
if AI_ADAPTER not in {"disabled", "openrouter"}:
    raise ImproperlyConfigured("Production AI adapter is unsupported.")
if AI_ENABLED and (AI_ADAPTER != "openrouter" or not AI_OPENROUTER_API_KEY or not AI_MODEL):
    raise ImproperlyConfigured(
        "Enabled production AI requires OpenRouter and complete configuration."
    )

MAINTENANCE_MODE = parse_bool("MAINTENANCE_MODE", default=False)
MFA_ENFORCED = parse_bool("MFA_ENFORCED", default=False)
MFA_ENCRYPTION_KEY = os.environ.get("MFA_ENCRYPTION_KEY", "").strip()
WEBAUTHN_RP_ID = os.environ.get("WEBAUTHN_RP_ID", "").strip()
WEBAUTHN_ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "").strip()
WEBAUTHN_RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "").strip()
if MFA_ENFORCED:
    try:
        Fernet(MFA_ENCRYPTION_KEY.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ImproperlyConfigured("MFA encryption configuration is invalid.") from exc
    if not WEBAUTHN_RP_NAME:
        raise ImproperlyConfigured("WebAuthn relying-party name is required.")
    if (
        not WEBAUTHN_RP_ID
        or "://" in WEBAUTHN_RP_ID
        or "/" in WEBAUTHN_RP_ID
        or len(WEBAUTHN_RP_ID) > 253
    ):
        raise ImproperlyConfigured("WebAuthn RP configuration is invalid.")
    if not WEBAUTHN_ORIGIN.startswith("https://") or WEBAUTHN_ORIGIN.count("/") != 2:
        raise ImproperlyConfigured("WebAuthn origin must be one protected origin.")
SERVICE_ROLE = require_value("SERVICE_ROLE")
if SERVICE_ROLE not in {"web", "worker", "migration"}:
    raise ImproperlyConfigured("SERVICE_ROLE is unsupported.")

RELEASE_VERSION = require_value("RELEASE_VERSION")
SOURCE_COMMIT = require_value("SOURCE_COMMIT")
BUILD_IDENTIFIER = require_value("BUILD_IDENTIFIER")
CONFIGURATION_SCHEMA_VERSION = require_value("CONFIGURATION_SCHEMA_VERSION")
for name, value in (
    ("RELEASE_VERSION", RELEASE_VERSION),
    ("SOURCE_COMMIT", SOURCE_COMMIT),
    ("BUILD_IDENTIFIER", BUILD_IDENTIFIER),
    ("CONFIGURATION_SCHEMA_VERSION", CONFIGURATION_SCHEMA_VERSION),
):
    if len(value) > 64 or not value.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise ImproperlyConfigured(f"{name} has an invalid bounded format.")

if not parse_bool("TRUST_PROXY_HEADERS", default=False):
    raise ImproperlyConfigured("Production requires explicit trusted proxy configuration.")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = parse_csv("DJANGO_CSRF_TRUSTED_ORIGINS", required=True)
if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Production CSRF trusted origins must use protected transport.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

DATA_UPLOAD_MAX_MEMORY_SIZE = parse_int(
    "MAX_REQUEST_BYTES", default=4_100_000, minimum=1024, maximum=10_000_000
)
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STORAGES = private_storage_settings(MEDIA_ROOT)  # noqa: F405
STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
    raise ImproperlyConfigured("LOG_LEVEL is unsupported.")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"privacy_json": {"()": "operations.logging.PrivacySafeJsonFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "privacy_json"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

if os.environ.get("STRANGE_NOVELTY_ENV", "").casefold() != "production":
    raise ImproperlyConfigured("STRANGE_NOVELTY_ENV must explicitly select production.")
