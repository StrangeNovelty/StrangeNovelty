import os

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character, CharacterPersonalityTrait, CharacterRelationship
from workspaces.models import Workspace, WorkspaceGrant
from worldbuilding.models import CodexEntry, Location

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_workspace(email):
    account = Account.objects.create_user(email, password="Synthetic-Only!")
    workspace = Workspace.objects.create(name=f"Synthetic {email}")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    return workspace, client


def test_personality_sliders_and_relationship_web_are_workspace_scoped():
    workspace, client = setup_workspace("cast@example.invalid")
    source = Character.objects.create(workspace=workspace, name="Synthetic A")
    target = Character.objects.create(workspace=workspace, name="Synthetic B")
    response = client.post(
        reverse("character-personality-trait-create", args=(source.id,)),
        {
            "name": "Reserve to candor",
            "score": 2,
            "low_label": "Guarded",
            "high_label": "Open",
            "notes": "Synthetic only",
            "order": 1,
        },
    )
    assert response.status_code == 303
    trait = CharacterPersonalityTrait.objects.get(character=source)
    assert trait.score == 2
    CharacterRelationship.objects.create(
        workspace=workspace,
        source=min(source, target, key=lambda item: item.id),
        target=max(source, target, key=lambda item: item.id),
        relationship_type="ally",
    )
    web = client.get(reverse("character-relationship-web"))
    assert web.status_code == 200
    assert b"Synthetic A" in web.content and b"Synthetic B" in web.content
    other_workspace, other_client = setup_workspace("other-cast@example.invalid")
    del other_workspace
    assert b"Synthetic A" not in other_client.get(reverse("character-relationship-web")).content


def test_world_bible_reads_structured_world_records_without_copying():
    workspace, client = setup_workspace("world@example.invalid")
    Location.objects.create(workspace=workspace, name="Synthetic Crossing")
    CodexEntry.objects.create(workspace=workspace, term="Synthetic Principle")
    response = client.get(reverse("world-bible"))
    assert response.status_code == 200
    assert b"Synthetic Crossing" in response.content
    assert b"Synthetic Principle" in response.content
    assert Location.objects.filter(workspace=workspace).count() == 1
    assert CodexEntry.objects.filter(workspace=workspace).count() == 1
