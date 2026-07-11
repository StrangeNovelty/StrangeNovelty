"""Local development settings; never use for production."""

import os

from .base import *  # noqa: F403
from .environment import parse_bool, parse_csv, postgres_database, require_value

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-placeholder-not-for-production")
DEBUG = parse_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = parse_csv("DJANGO_ALLOWED_HOSTS") or ["localhost", "127.0.0.1"]
DATABASES = {"default": postgres_database(require_value("DATABASE_URL"), require_credentials=False)}
