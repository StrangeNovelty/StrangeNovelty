"""Small, fail-closed helpers for environment-backed Django settings."""

import os
from collections.abc import Mapping
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def require_value(name: str, *, environ: Mapping[str, str] | None = None) -> str:
    """Return a required non-empty setting without exposing its value in errors."""
    source = os.environ if environ is None else environ
    value = source.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Required setting {name} is missing or empty.")
    return value


def parse_bool(name: str, *, default: bool | None = None) -> bool:
    """Parse a strict boolean setting."""
    raw = os.environ.get(name)
    if raw is None:
        if default is None:
            raise ImproperlyConfigured(f"Required setting {name} is missing.")
        return default

    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"Setting {name} must be an explicit boolean.")


def parse_csv(name: str, *, required: bool = False) -> list[str]:
    """Parse a comma-separated list, rejecting empty required lists."""
    raw = os.environ.get(name, "")
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if required and not values:
        raise ImproperlyConfigured(f"Required setting {name} is missing or empty.")
    return values


def parse_int(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"Setting {name} must be an integer.") from exc
    if value < minimum or value > maximum:
        raise ImproperlyConfigured(f"Setting {name} is outside its supported bounds.")
    return value


def postgres_database(
    url: str,
    *,
    require_credentials: bool,
) -> dict[str, object]:
    """Parse an explicit PostgreSQL URL into Django's database configuration."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ImproperlyConfigured("DATABASE_URL is invalid.") from exc

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL.")

    name = unquote(parsed.path.lstrip("/"))
    if not name or not parsed.hostname:
        raise ImproperlyConfigured("DATABASE_URL must include a database name and host.")

    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    if require_credentials and (not username or not password):
        raise ImproperlyConfigured("Production DATABASE_URL must include explicit credentials.")

    config: dict[str, object] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "HOST": parsed.hostname,
        "PORT": str(port or 5432),
        "CONN_MAX_AGE": 0,
    }
    if username:
        config["USER"] = username
    if password:
        config["PASSWORD"] = password
    return config
