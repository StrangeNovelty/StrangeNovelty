from pathlib import Path

import pytest
from botocore.exceptions import ClientError
from django.core.exceptions import ImproperlyConfigured

from strange_novelty.file_delivery import PrivateObjectUnavailable, open_private_object
from strange_novelty.settings.storage import private_storage_settings


def test_filesystem_storage_has_separate_private_aliases(monkeypatch, tmp_path):
    monkeypatch.delenv("PRIVATE_STORAGE_BACKEND", raising=False)
    configured = private_storage_settings(Path(tmp_path))
    assert set(configured) == {"default", "private", "exports"}
    assert all(
        value["BACKEND"] == "django.core.files.storage.FileSystemStorage"
        for value in configured.values()
    )
    assert all("OPTIONS" not in value for value in configured.values())


def test_s3_storage_is_private_non_overwriting_and_prefixed(monkeypatch):
    values = {
        "PRIVATE_STORAGE_BACKEND": "s3",
        "PRIVATE_STORAGE_BUCKET": "synthetic-private-bucket",
        "PRIVATE_STORAGE_ENDPOINT_URL": "https://objects.example.invalid",
        "PRIVATE_STORAGE_REGION": "auto",
        "PRIVATE_STORAGE_ACCESS_KEY_ID": "synthetic-access-key",
        "PRIVATE_STORAGE_SECRET_ACCESS_KEY": "synthetic-secret-key",
        "PRIVATE_STORAGE_UPLOAD_PREFIX": "author/uploads",
        "PRIVATE_STORAGE_EXPORT_PREFIX": "author/exports",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    configured = private_storage_settings(Path("/unused"))
    assert configured["private"]["OPTIONS"]["location"] == "author/uploads"
    assert configured["exports"]["OPTIONS"]["location"] == "author/exports"
    for alias in ("default", "private", "exports"):
        options = configured[alias]["OPTIONS"]
        assert configured[alias]["BACKEND"] == "storages.backends.s3.S3Storage"
        assert options["default_acl"] is None
        assert options["file_overwrite"] is False
        assert options["querystring_auth"] is True
        assert options["object_parameters"] == {"CacheControl": "private, no-store"}


@pytest.mark.parametrize(
    "missing",
    (
        "PRIVATE_STORAGE_BUCKET",
        "PRIVATE_STORAGE_ENDPOINT_URL",
        "PRIVATE_STORAGE_ACCESS_KEY_ID",
        "PRIVATE_STORAGE_SECRET_ACCESS_KEY",
    ),
)
def test_s3_storage_requires_complete_configuration(monkeypatch, missing):
    values = {
        "PRIVATE_STORAGE_BACKEND": "s3",
        "PRIVATE_STORAGE_BUCKET": "bucket",
        "PRIVATE_STORAGE_ENDPOINT_URL": "https://objects.example.invalid",
        "PRIVATE_STORAGE_ACCESS_KEY_ID": "access",
        "PRIVATE_STORAGE_SECRET_ACCESS_KEY": "secret",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv(missing)
    with pytest.raises(ImproperlyConfigured, match=missing):
        private_storage_settings(Path("/unused"))


def test_storage_backend_and_prefix_validation(monkeypatch):
    monkeypatch.setenv("PRIVATE_STORAGE_BACKEND", "public-cloud")
    with pytest.raises(ImproperlyConfigured, match="filesystem or s3"):
        private_storage_settings(Path("/unused"))

    monkeypatch.setenv("PRIVATE_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("PRIVATE_STORAGE_BUCKET", "bucket")
    monkeypatch.setenv("PRIVATE_STORAGE_ENDPOINT_URL", "https://objects.example.invalid")
    monkeypatch.setenv("PRIVATE_STORAGE_ACCESS_KEY_ID", "access")
    monkeypatch.setenv("PRIVATE_STORAGE_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("PRIVATE_STORAGE_UPLOAD_PREFIX", "../private")
    with pytest.raises(ImproperlyConfigured, match="safe storage prefix"):
        private_storage_settings(Path("/unused"))


def test_remote_missing_object_is_normalized_without_using_path():
    class MissingFieldFile:
        def open(self, mode):
            assert mode == "rb"
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "synthetic missing object"}},
                "GetObject",
            )

        @property
        def path(self):  # pragma: no cover - proves the delivery helper never asks for it
            raise AssertionError("Remote private objects do not have filesystem paths.")

    with pytest.raises(PrivateObjectUnavailable):
        open_private_object(MissingFieldFile())
