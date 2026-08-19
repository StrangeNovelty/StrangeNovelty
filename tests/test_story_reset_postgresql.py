import os
from io import StringIO
from typing import cast

import pytest
from django.core.management import call_command

from accounts.models import Account
from characters.models import Character
from decks.models import Deck
from library.models import ResearchSource
from stories.models import Work
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]


def test_story_reset_inventory_is_workspace_scoped_and_read_only() -> None:
    account = Account.objects.create_user(
        "story-reset@example.invalid", password="Synthetic-Story-Reset-Only!"
    )
    workspace = cast(Workspace, Workspace.objects.create(name="Story Reset Workspace"))
    other_workspace = cast(Workspace, Workspace.objects.create(name="Other Workspace"))
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    Character.objects.create(workspace=workspace, name="Incorrect Character")
    Character.objects.create(workspace=other_workspace, name="Other Character")
    Work.objects.create(
        workspace=workspace,
        title="Incorrect Work",
        work_type=Work.WorkType.NOVEL,
    )
    deck = Deck.objects.create(
        workspace=workspace,
        name="Reference Deck",
        source_identity="synthetic:reference-deck",
    )
    source = ResearchSource.objects.create(
        workspace=workspace,
        title="Review Before Reset",
    )

    output = StringIO()
    call_command("inspect_story_reset", workspace=str(workspace.id), stdout=output)

    rendered = output.getvalue()
    assert "mode=read-only" in rendered
    assert "characters.Character=1" in rendered
    assert "stories.Work=1" in rendered
    assert "decks.Deck=1" in rendered
    assert "library.ResearchSource=1" in rendered
    assert "No records were changed" in rendered
    assert Character.objects.count() == 2
    assert Work.objects.filter(workspace=workspace).exists()
    assert Deck.objects.filter(id=deck.id).exists()
    assert ResearchSource.objects.filter(id=source.id).exists()
    assert Workspace.objects.filter(id=workspace.id).exists()
    assert Account.objects.filter(id=account.id).exists()
