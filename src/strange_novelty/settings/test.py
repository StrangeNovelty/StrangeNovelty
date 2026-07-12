"""Test settings using an explicit PostgreSQL-only test configuration."""

import os

from .base import *  # noqa: F403
from .environment import postgres_database

SECRET_KEY = "test-only-placeholder-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]

_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://test-only:test-only@postgresql.invalid:5432/strange_novelty_test",
)
DATABASES = {"default": postgres_database(_TEST_DATABASE_URL, require_credentials=True)}
AI_ENABLED = False
AI_ADAPTER = "disabled"
MAINTENANCE_MODE = False
SERVICE_ROLE = "web"

PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
