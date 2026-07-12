"""Fail-closed production settings."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .environment import parse_bool, parse_csv, parse_int, postgres_database, require_value

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
if AI_ENABLED:
    raise ImproperlyConfigured(
        "Production AI cannot be enabled until a reviewed provider adapter is configured."
    )

MAINTENANCE_MODE = parse_bool("MAINTENANCE_MODE", default=False)
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
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

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
