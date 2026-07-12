"""Local development settings; never use for production."""

import os

from .base import *  # noqa: F403
from .environment import parse_bool, parse_csv, postgres_database, require_value

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-placeholder-not-for-production")
DEBUG = parse_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = parse_csv("DJANGO_ALLOWED_HOSTS") or ["localhost", "127.0.0.1"]
DATABASES = {"default": postgres_database(require_value("DATABASE_URL"), require_credentials=False)}
AI_ENABLED = parse_bool("AI_ENABLED", default=False)
AI_ADAPTER = os.environ.get("AI_ADAPTER", "disabled").strip()
MAINTENANCE_MODE = parse_bool("MAINTENANCE_MODE", default=False)
SERVICE_ROLE = "web"
if AI_ADAPTER not in {"disabled", "local_fake"}:
    raise ValueError("Local AI_ADAPTER is unsupported.")
if AI_ENABLED and AI_ADAPTER != "local_fake":
    raise ValueError("Local AI requires the explicit local_fake adapter.")
