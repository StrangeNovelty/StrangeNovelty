import os
import subprocess
import sys
from collections.abc import Mapping

from django.conf import settings


def _settings_import(
    module: str, values: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": "src",
        "DJANGO_SETTINGS_MODULE": module,
    }
    if values:
        environment.update(values)

    return subprocess.run(
        [sys.executable, "-c", "import django; django.setup()"],
        cwd=os.getcwd(),
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _valid_production_environment() -> dict[str, str]:
    return {
        "STRANGE_NOVELTY_ENV": "production",
        "DJANGO_SECRET_KEY": "s" * 64,
        "DJANGO_DEBUG": "false",
        "DJANGO_ALLOWED_HOSTS": "app.example.invalid",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://app.example.invalid",
        "DATABASE_URL": (
            "postgresql://production-user:production-password@"
            "db.example.invalid:5432/strange_novelty"
        ),
        "TRUST_PROXY_HEADERS": "true",
        "SERVICE_ROLE": "web",
        "RELEASE_VERSION": "v1-test",
        "SOURCE_COMMIT": "a" * 40,
        "BUILD_IDENTIFIER": "build-test",
        "CONFIGURATION_SCHEMA_VERSION": "config-v1",
    }


def test_test_settings_use_postgresql_without_sqlite_fallback() -> None:
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.postgresql"
    assert "sqlite" not in database["ENGINE"]
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"


def test_local_settings_import_with_explicit_postgresql_url() -> None:
    result = _settings_import(
        "strange_novelty.settings.local",
        {
            "DATABASE_URL": (
                "postgresql://local-user:local-password@127.0.0.1:5432/strange_novelty_local"
            )
        },
    )

    assert result.returncode == 0, result.stderr


def test_production_settings_fail_when_required_values_are_absent() -> None:
    result = _settings_import("strange_novelty.settings.production")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr
    assert "production-password" not in result.stderr


def test_production_settings_import_with_safe_explicit_values() -> None:
    result = _settings_import(
        "strange_novelty.settings.production", _valid_production_environment()
    )

    assert result.returncode == 0, result.stderr


def test_production_settings_reject_debug() -> None:
    environment = _valid_production_environment()
    environment["DJANGO_DEBUG"] = "true"

    result = _settings_import("strange_novelty.settings.production", environment)

    assert result.returncode != 0
    assert "DJANGO_DEBUG must be false" in result.stderr


def test_production_settings_reject_wildcard_host() -> None:
    environment = _valid_production_environment()
    environment["DJANGO_ALLOWED_HOSTS"] = "*"

    result = _settings_import("strange_novelty.settings.production", environment)

    assert result.returncode != 0
    assert "Wildcard ALLOWED_HOSTS" in result.stderr


def test_production_settings_reject_non_postgresql_database() -> None:
    environment = _valid_production_environment()
    environment["DATABASE_URL"] = "sqlite:///not-allowed.sqlite3"

    result = _settings_import("strange_novelty.settings.production", environment)

    assert result.returncode != 0
    assert "must use PostgreSQL" in result.stderr
