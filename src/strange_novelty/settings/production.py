"""Fail-closed production settings."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .environment import parse_bool, parse_csv, postgres_database, require_value

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

AI_ENABLED = parse_bool("AI_ENABLED", default=False)
AI_ADAPTER = os.environ.get("AI_ADAPTER", "disabled").strip()
if AI_ENABLED:
    raise ImproperlyConfigured(
        "Production AI cannot be enabled until a reviewed provider adapter is configured."
    )

CSRF_TRUSTED_ORIGINS = parse_csv("DJANGO_CSRF_TRUSTED_ORIGINS", required=True)
if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured("Production CSRF trusted origins must use protected transport.")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

if os.environ.get("STRANGE_NOVELTY_ENV", "").casefold() != "production":
    raise ImproperlyConfigured("STRANGE_NOVELTY_ENV must explicitly select production.")
