import os
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from workspaces.models import OwnerBootstrap, Workspace, WorkspaceGrant
from workspaces.services import get_authorized_workspace

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

TEST_PASSWORD = "Synthetic-Phase2-Password-Only!"


def _account(email: str = "owner@example.invalid", **fields: bool) -> Account:
    return Account.objects.create_user(email, password=TEST_PASSWORD, **fields)


def _owner_workspace(account: Account) -> tuple[Workspace, WorkspaceGrant]:
    workspace = Workspace.objects.create(name="Synthetic Workspace")
    grant = WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return workspace, grant


def test_normalized_email_login_and_private_landing(client: Client) -> None:
    account = _account()
    _owner_workspace(account)

    response = client.post(
        reverse("login"),
        {"username": "  OWNER@EXAMPLE.INVALID ", "password": TEST_PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse("workspace-home")
    landing = client.get(reverse("workspace-home"))
    assert landing.status_code == 200
    assert b"Synthetic Workspace" in landing.content
    assert "no-store" in landing.headers["Cache-Control"]


def test_invalid_and_inactive_login_use_generic_message(client: Client) -> None:
    inactive = _account("inactive@example.invalid", is_active=False)

    unknown_response = client.post(
        reverse("login"),
        {"username": "unknown@example.invalid", "password": TEST_PASSWORD},
    )
    inactive_response = client.post(
        reverse("login"),
        {"username": inactive.email, "password": TEST_PASSWORD},
    )

    message = b"Unable to sign in with those credentials."
    assert unknown_response.status_code == 200
    assert inactive_response.status_code == 200
    assert message in unknown_response.content
    assert message in inactive_response.content


def test_login_rotates_existing_session_key(client: Client) -> None:
    account = _account()
    _owner_workspace(account)
    session = client.session
    session["synthetic"] = "value"
    session.save()
    previous_key = session.session_key

    response = client.post(reverse("login"), {"username": account.email, "password": TEST_PASSWORD})

    assert response.status_code == 302
    assert client.session.session_key != previous_key


def test_logout_is_post_only_and_invalidates_session(client: Client) -> None:
    account = _account()
    _owner_workspace(account)
    client.force_login(account)

    assert client.get(reverse("logout")).status_code == 405
    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == reverse("login")
    assert "_auth_user_id" not in client.session


def test_login_and_logout_require_csrf() -> None:
    account = _account()
    _owner_workspace(account)
    client = Client(enforce_csrf_checks=True)

    assert (
        client.post(
            reverse("login"), {"username": account.email, "password": TEST_PASSWORD}
        ).status_code
        == 403
    )

    client.force_login(account)
    assert client.post(reverse("logout")).status_code == 403


def test_safe_next_is_honored_and_external_next_is_rejected(client: Client) -> None:
    account = _account()
    _owner_workspace(account)

    safe = client.post(
        f"{reverse('login')}?next={reverse('workspace-home')}",
        {"username": account.email, "password": TEST_PASSWORD},
    )
    assert safe.url == reverse("workspace-home")

    client.post(reverse("logout"))
    external = client.post(
        f"{reverse('login')}?next=https://example.invalid/elsewhere",
        {"username": account.email, "password": TEST_PASSWORD},
    )
    assert external.url == reverse("workspace-home")


def test_workspace_page_requires_login(client: Client) -> None:
    response = client.get(reverse("workspace-home"))

    assert response.status_code == 302
    assert response.url.startswith(f"{reverse('login')}?next=")


def test_missing_revoked_and_staff_only_grants_deny_immediately(client: Client) -> None:
    account = _account(is_staff=True, is_superuser=True)
    workspace, grant = _owner_workspace(account)
    client.force_login(account)

    assert client.get(reverse("workspace-home")).status_code == 200
    grant.state = WorkspaceGrant.State.REVOKED
    grant.revoked_at = timezone.now()
    grant.save(update_fields=("state", "revoked_at", "updated_at"))
    assert client.get(reverse("workspace-home")).status_code == 404

    with pytest.raises(Http404):
        get_authorized_workspace(account, workspace.id)


def test_cross_workspace_access_is_denied_without_disclosure() -> None:
    account = _account()
    _owner_workspace(account)
    other = Workspace.objects.create(name="Other Synthetic Workspace")

    with pytest.raises(Http404, match="Workspace is unavailable"):
        get_authorized_workspace(account, other.id)


def test_unique_active_grant_and_state_constraints() -> None:
    account = _account()
    workspace, _ = _owner_workspace(account)

    with pytest.raises(IntegrityError), transaction.atomic():
        WorkspaceGrant.objects.create(
            account=account,
            workspace=workspace,
            role=WorkspaceGrant.Role.OWNER,
            state=WorkspaceGrant.State.ACTIVE,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        WorkspaceGrant.objects.create(
            account=account,
            workspace=Workspace.objects.create(name="Invalid State Workspace"),
            role=WorkspaceGrant.Role.OWNER,
            state=WorkspaceGrant.State.REVOKED,
            revoked_at=None,
        )


def test_bootstrap_is_atomic_idempotent_and_never_prints_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = StringIO()
    monkeypatch.setenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD", TEST_PASSWORD)

    call_command(
        "bootstrap_owner",
        email="  OWNER@EXAMPLE.INVALID ",
        workspace_name="Synthetic Workspace",
        no_input=True,
        stdout=output,
    )

    assert Account.objects.count() == 1
    assert Workspace.objects.count() == 1
    assert WorkspaceGrant.objects.count() == 1
    assert OwnerBootstrap.objects.count() == 1
    account = Account.objects.get()
    assert account.email == "owner@example.invalid"
    assert account.check_password(TEST_PASSWORD)
    assert TEST_PASSWORD not in output.getvalue()

    monkeypatch.delenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD")
    call_command(
        "bootstrap_owner",
        email="owner@example.invalid",
        workspace_name="Synthetic Workspace",
        no_input=True,
        stdout=output,
    )
    assert Account.objects.count() == 1
    assert Workspace.objects.count() == 1
    assert WorkspaceGrant.objects.count() == 1


def test_conflicting_bootstrap_fails_without_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD", TEST_PASSWORD)
    call_command(
        "bootstrap_owner",
        email="owner@example.invalid",
        workspace_name="Synthetic Workspace",
        no_input=True,
        stdout=StringIO(),
    )

    with pytest.raises(CommandError, match="conflicts"):
        call_command(
            "bootstrap_owner",
            email="different@example.invalid",
            workspace_name="Different Workspace",
            no_input=True,
            stdout=StringIO(),
        )

    assert Account.objects.count() == 1
    assert Workspace.objects.count() == 1
    assert WorkspaceGrant.objects.count() == 1


def test_bootstrap_partial_failure_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STRANGE_NOVELTY_BOOTSTRAP_PASSWORD", TEST_PASSWORD)

    with (
        patch.object(
            WorkspaceGrant.objects, "create", side_effect=RuntimeError("synthetic failure")
        ),
        pytest.raises(RuntimeError, match="synthetic failure"),
    ):
        call_command(
            "bootstrap_owner",
            email="owner@example.invalid",
            workspace_name="Synthetic Workspace",
            no_input=True,
            stdout=StringIO(),
        )

    assert Account.objects.count() == 0
    assert Workspace.objects.count() == 0
    assert WorkspaceGrant.objects.count() == 0
    assert OwnerBootstrap.objects.count() == 0


def test_workspace_uuid_is_not_visible_on_landing(client: Client) -> None:
    account = _account()
    workspace, _ = _owner_workspace(account)
    client.force_login(account)

    response = client.get(reverse("workspace-home"))

    assert str(workspace.id).encode() not in response.content
