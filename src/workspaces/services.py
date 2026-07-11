import uuid
from typing import cast

from django.contrib.auth.models import AnonymousUser
from django.http import Http404

from accounts.models import Account
from workspaces.models import Workspace, WorkspaceGrant


def get_authorized_workspace(
    account: Account | AnonymousUser,
    workspace_id: uuid.UUID,
) -> Workspace:
    """Resolve one active Workspace through an active owner Grant or disclose nothing."""
    if not account.is_authenticated or not account.is_active:
        raise Http404("Workspace is unavailable.")

    try:
        return cast(
            Workspace,
            Workspace.objects.get(
                id=workspace_id,
                is_active=True,
                grants__account=account,
                grants__role=WorkspaceGrant.Role.OWNER,
                grants__state=WorkspaceGrant.State.ACTIVE,
            ),
        )
    except (Workspace.DoesNotExist, Workspace.MultipleObjectsReturned) as exc:
        raise Http404("Workspace is unavailable.") from exc


def resolve_owner_workspace(account: Account | AnonymousUser) -> Workspace:
    """Resolve the Version 1 owner's single active Workspace on each request."""
    if not account.is_authenticated or not account.is_active:
        raise Http404("Workspace is unavailable.")

    try:
        return cast(
            Workspace,
            Workspace.objects.get(
                is_active=True,
                grants__account=account,
                grants__role=WorkspaceGrant.Role.OWNER,
                grants__state=WorkspaceGrant.State.ACTIVE,
            ),
        )
    except (Workspace.DoesNotExist, Workspace.MultipleObjectsReturned) as exc:
        raise Http404("Workspace is unavailable.") from exc
