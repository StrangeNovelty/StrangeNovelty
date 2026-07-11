import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings

from accounts.models import Account


def test_auth_user_model_uses_project_account() -> None:
    assert settings.AUTH_USER_MODEL == "accounts.Account"


def test_account_uses_uuid_primary_key() -> None:
    account = Account(email="owner@example.invalid")

    assert isinstance(account.pk, uuid.UUID)
    assert Account._meta.pk.name == "id"
    assert Account._meta.pk.get_internal_type() == "UUIDField"


def test_email_normalization_is_consistent() -> None:
    normalized = Account.objects.normalize_login_email("  Owner+Writing@EXAMPLE.INVALID  ")

    assert normalized == "owner+writing@example.invalid"


@patch.object(Account, "save", autospec=True)
def test_create_user_normalizes_email_and_hashes_password(
    mock_save: MagicMock,
) -> None:
    account = Account.objects.create_user(
        "  Owner@EXAMPLE.INVALID ", password="synthetic-test-password"
    )

    assert account.email == "owner@example.invalid"
    assert account.is_staff is False
    assert account.is_superuser is False
    assert account.password != "synthetic-test-password"
    assert account.check_password("synthetic-test-password")
    mock_save.assert_called_once_with(account, using=None)


@pytest.mark.parametrize("email", ["", "   "])
def test_create_user_rejects_missing_email(email: str) -> None:
    with pytest.raises(ValueError, match="email address is required"):
        Account.objects.create_user(email, password="synthetic-test-password")


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"is_staff": False}, "is_staff=True"),
        ({"is_superuser": False}, "is_superuser=True"),
        ({"is_active": False}, "is_active=True"),
    ],
)
def test_create_superuser_rejects_false_invariants(override: dict[str, bool], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Account.objects.create_superuser(
            "owner@example.invalid",
            password="synthetic-test-password",
            **override,
        )


def test_create_superuser_rejects_missing_password() -> None:
    with pytest.raises(ValueError, match="superuser password is required"):
        Account.objects.create_superuser("owner@example.invalid", password=None)


@patch.object(Account, "save", autospec=True)
def test_create_superuser_sets_required_invariants(mock_save: MagicMock) -> None:
    account = Account.objects.create_superuser(
        "Owner@EXAMPLE.INVALID", password="synthetic-test-password"
    )

    assert account.email == "owner@example.invalid"
    assert account.is_active is True
    assert account.is_staff is True
    assert account.is_superuser is True
    assert account.check_password("synthetic-test-password")
    mock_save.assert_called_once_with(account, using=None)


def test_account_string_is_normalized_email() -> None:
    account = Account(email="owner@example.invalid")

    assert str(account) == "owner@example.invalid"
