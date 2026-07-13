import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.db import models
from django.http import Http404
from django.test import RequestFactory
from django.urls import resolve

from accounts.admin import AccountAdmin
from accounts.forms import (
    AccountChangeAdminForm,
    AccountCreationAdminForm,
    EmailAuthenticationForm,
)
from accounts.models import Account
from workspaces.models import OwnerBootstrap, Workspace, WorkspaceGrant
from workspaces.services import get_authorized_workspace, resolve_owner_workspace
from workspaces.views import root, workspace_home


def test_workspace_and_grant_use_uuid_primary_keys() -> None:
    workspace = Workspace(name="Synthetic Workspace")
    grant = WorkspaceGrant(workspace=workspace, account=Account())

    assert isinstance(workspace.pk, uuid.UUID)
    assert isinstance(grant.pk, uuid.UUID)
    assert Workspace._meta.pk.get_internal_type() == "UUIDField"
    assert WorkspaceGrant._meta.pk.get_internal_type() == "UUIDField"


def test_workspace_foreign_keys_are_protective() -> None:
    assert WorkspaceGrant._meta.get_field("workspace").remote_field.on_delete is models.PROTECT
    assert WorkspaceGrant._meta.get_field("account").remote_field.on_delete is models.PROTECT
    assert OwnerBootstrap._meta.get_field("workspace").remote_field.on_delete is models.PROTECT
    assert OwnerBootstrap._meta.get_field("account").remote_field.on_delete is models.PROTECT


def test_grant_role_vocabulary_is_owner_only() -> None:
    assert list(WorkspaceGrant.Role.values) == ["owner"]
    assert set(WorkspaceGrant.State.values) == {"active", "revoked"}


def test_grant_constraints_and_indexes_are_explicit() -> None:
    constraint_names = {constraint.name for constraint in WorkspaceGrant._meta.constraints}
    index_names = {index.name for index in WorkspaceGrant._meta.indexes}

    assert constraint_names == {
        "unique_active_account_workspace_grant",
        "workspace_grant_state_timestamp_consistent",
    }
    assert index_names == {"grant_account_state_idx", "grant_workspace_state_idx"}


def test_account_admin_uses_project_forms_without_username() -> None:
    registered = admin.site._registry[Account]

    assert isinstance(registered, AccountAdmin)
    assert registered.form is AccountChangeAdminForm
    assert registered.add_form is AccountCreationAdminForm
    assert "username" not in AccountCreationAdminForm.base_fields
    assert "username" not in AccountChangeAdminForm.base_fields


def test_login_form_uses_email_and_generic_errors() -> None:
    assert EmailAuthenticationForm.base_fields["username"].label == "Email"
    assert EmailAuthenticationForm.error_messages["invalid_login"] == (
        "Unable to sign in with those credentials."
    )
    assert EmailAuthenticationForm.error_messages["inactive"] == (
        "Unable to sign in with those credentials."
    )


def test_logout_route_does_not_allow_get() -> None:
    view_class = resolve("/logout/").func.view_class

    assert "post" in view_class.http_method_names
    assert "get" not in view_class.http_method_names


def test_authorization_service_scopes_every_lookup() -> None:
    account = SimpleNamespace(is_authenticated=True, is_active=True)
    workspace_id = uuid.uuid4()
    expected = Workspace(id=workspace_id, name="Synthetic Workspace")

    with patch.object(Workspace.objects, "get", return_value=expected) as get_workspace:
        assert get_authorized_workspace(account, workspace_id) is expected

    get_workspace.assert_called_once_with(
        id=workspace_id,
        is_active=True,
        grants__account=account,
        grants__role=WorkspaceGrant.Role.OWNER,
        grants__state=WorkspaceGrant.State.ACTIVE,
    )


def test_authorization_service_hides_missing_or_inaccessible_workspace() -> None:
    account = SimpleNamespace(is_authenticated=True, is_active=True)

    with (
        patch.object(Workspace.objects, "get", side_effect=Workspace.DoesNotExist),
        pytest.raises(Http404, match="Workspace is unavailable"),
    ):
        get_authorized_workspace(account, uuid.uuid4())


def test_owner_workspace_resolution_requires_active_owner_grant() -> None:
    account = SimpleNamespace(is_authenticated=True, is_active=True)
    expected = Workspace(name="Synthetic Workspace")

    with patch.object(Workspace.objects, "get", return_value=expected) as get_workspace:
        assert resolve_owner_workspace(account) is expected

    get_workspace.assert_called_once_with(
        is_active=True,
        grants__account=account,
        grants__role=WorkspaceGrant.Role.OWNER,
        grants__state=WorkspaceGrant.State.ACTIVE,
    )


def test_workspace_views_are_private_and_non_cacheable() -> None:
    request = RequestFactory().get("/workspace/")
    request.user = SimpleNamespace(is_authenticated=True, is_active=True)
    workspace = Workspace(name="Synthetic Workspace")

    with patch("workspaces.views.resolve_owner_workspace", return_value=workspace):
        response = workspace_home(request)

    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    assert b"Synthetic Workspace" in response.content
    assert str(workspace.id).encode() not in response.content


def test_workspace_template_preserves_shell_navigation_and_search_contract() -> None:
    template = (Path(__file__).parents[1] / "templates/workspaces/home.html").read_text(
        encoding="utf-8"
    )
    assert 'class="app-shell"' in template
    assert 'class="nav-link nav-link-active"' in template
    assert '<form method="post" action="{% url \'logout\' %}">' in template
    assert '<form class="header-search" method="post"' in template
    assert "{% csrf_token %}" in template
    assert 'name="query"' in template
    assert "{% url 'scene-list' %}" in template
    assert "{% url 'scene-create' %}" in template
    assert "{% url 'scene-search' %}" in template
    assert "{% url 'scene-editor' scene_id=scene.id %}" in template
    assert '<main class="workspace-main' not in template


def test_workspace_dashboard_text_wraps_at_narrow_widths() -> None:
    stylesheet = (Path(__file__).parents[1] / "static/strange_novelty/app.css").read_text(
        encoding="utf-8"
    )
    assert ".workspace-header h1 {" in stylesheet
    assert ".recent-scene-title {\n  min-width: 0;\n  overflow-wrap: anywhere;" in stylesheet
    assert ".card-support {\n  overflow-wrap: anywhere;" in stylesheet
    assert ".recent-scene {\n    align-items: flex-start;" in stylesheet


def test_root_redirects_by_authentication_state() -> None:
    anonymous_request = RequestFactory().get("/")
    anonymous_request.user = SimpleNamespace(is_authenticated=False)
    authenticated_request = RequestFactory().get("/")
    authenticated_request.user = SimpleNamespace(is_authenticated=True)

    assert root(anonymous_request).url == "/login/"
    assert root(authenticated_request).url == "/workspace/"
