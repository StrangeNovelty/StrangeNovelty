"""Provider-neutral private-file storage configuration."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Required setting {name} is missing or empty.")
    return value


def _prefix(name: str, default: str) -> str:
    value = os.environ.get(name, default).strip().strip("/")
    if value in {".", ".."} or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ImproperlyConfigured(f"Setting {name} is not a safe storage prefix.")
    return value


def private_storage_settings(media_root: Path) -> dict[str, dict[str, object]]:
    backend = os.environ.get("PRIVATE_STORAGE_BACKEND", "filesystem").strip().casefold()
    if backend == "filesystem":
        return {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "private": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "exports": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        }
    if backend != "s3":
        raise ImproperlyConfigured("PRIVATE_STORAGE_BACKEND must be filesystem or s3.")

    bucket = _required("PRIVATE_STORAGE_BUCKET")
    endpoint = _required("PRIVATE_STORAGE_ENDPOINT_URL")
    access_key = _required("PRIVATE_STORAGE_ACCESS_KEY_ID")
    secret_key = _required("PRIVATE_STORAGE_SECRET_ACCESS_KEY")
    region = os.environ.get("PRIVATE_STORAGE_REGION", "").strip() or None
    addressing_style = os.environ.get("PRIVATE_STORAGE_ADDRESSING_STYLE", "auto").strip()
    if addressing_style not in {"auto", "path", "virtual"}:
        raise ImproperlyConfigured("PRIVATE_STORAGE_ADDRESSING_STYLE is unsupported.")
    signature_version = os.environ.get("PRIVATE_STORAGE_SIGNATURE_VERSION", "s3v4").strip()
    if signature_version not in {"s3", "s3v4"}:
        raise ImproperlyConfigured("PRIVATE_STORAGE_SIGNATURE_VERSION is unsupported.")

    common: dict[str, object] = {
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket_name": bucket,
        "endpoint_url": endpoint,
        "region_name": region,
        "default_acl": None,
        "file_overwrite": False,
        "querystring_auth": True,
        "addressing_style": addressing_style,
        "signature_version": signature_version,
        "object_parameters": {"CacheControl": "private, no-store"},
    }
    custom_domain = os.environ.get("PRIVATE_STORAGE_CUSTOM_DOMAIN", "").strip()
    if custom_domain:
        common["custom_domain"] = custom_domain

    def alias(location: str) -> dict[str, object]:
        return {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {**common, "location": location},
        }

    upload_prefix = _prefix("PRIVATE_STORAGE_UPLOAD_PREFIX", "uploads")
    export_prefix = _prefix("PRIVATE_STORAGE_EXPORT_PREFIX", "exports")
    return {
        "default": alias(upload_prefix),
        "private": alias(upload_prefix),
        "exports": alias(export_prefix),
    }
