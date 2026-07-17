import os

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character, CharacterGroup, GroupRelationship
from scenes.models import Scene
from scenes.services import create_scene
from stories.models import Chapter, Work
from stories.services import update_scene_placement
from stories.writing import summarize_chapter
from workspaces.models import Workspace, WorkspaceGrant
from worldbuilding.models import (
    CodexCharacterLink,
    CodexEntry,
    CodexRelation,
    Creature,
    CreatureCharacterLink,
    CreatureCodexLink,
    CreatureGroupLink,
    CreatureLocationLink,
    Location,
    LocationCharacterLink,
    Region,
    SceneLocationLink,
    WorldItem,
)
from worldbuilding.search import search_world

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]
PASSWORD = "Synthetic-Worldbuilding-Only!"


def owner(email: str = "world@example.invalid") -> tuple[Account, Workspace, Client]:
    account = Account.objects.create_user(email, password=PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic World")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    return account, workspace, client


def test_location_region_crud_search_cycles_protection_and_scope() -> None:
    account, workspace, client = owner()
    empty = client.get(reverse("world-record-list", args=("locations",)))
    assert empty.status_code == 200 and b"No Locations yet" in empty.content
    parent = Region.objects.create(workspace=workspace, name="North", region_type="territory")
    child = Region(workspace=workspace, name="March", region_type="province", parent=parent)
    child.full_clean()
    child.save()
    parent.parent = child
    with pytest.raises(ValidationError):
        parent.full_clean()
    response = client.post(
        reverse("world-record-create", args=("locations",)),
        {
            "name": "Glass Harbor",
            "aliases": "The Shards",
            "location_type": "city",
            "status": "active",
            "region": child.id,
            "summary": "A port of mirrored towers.",
        },
    )
    assert response.status_code == 302, response.context["form"].errors
    location = Location.objects.get(name="Glass Harbor")
    assert location.region == child
    assert (
        search_world(actor=account, workspace_id=workspace.id, query_text="mirrored")[
            "location_results"
        ][0].record
        == location
    )
    with pytest.raises(ProtectedError):
        child.delete()
    _, other, other_client = owner("world-other@example.invalid")
    assert (
        other_client.get(
            reverse("world-record-detail", args=("locations", location.id))
        ).status_code
        == 404
    )
    assert other != workspace


def test_factions_codex_relations_and_duplicate_guards() -> None:
    _, workspace, _ = owner()
    first = CharacterGroup.objects.create(
        workspace=workspace,
        name="Dawn Court",
        group_type="faction",
        alignment="allied",
        public_goals="Keep the roads open",
    )
    second = CharacterGroup.objects.create(
        workspace=workspace, name="Ash Court", group_type="organization", alignment="hostile"
    )
    source, target = sorted((first, second), key=lambda item: item.id)
    GroupRelationship.objects.create(
        workspace=workspace, source=source, target=target, relationship_type="hostile"
    )
    with pytest.raises(IntegrityError):
        GroupRelationship.objects.create(
            workspace=workspace, source=source, target=target, relationship_type="allied"
        )
    canon = CodexEntry.objects.create(
        workspace=workspace, term="The Accord", category="law", canon_state="canon"
    )
    disputed = CodexEntry.objects.create(
        workspace=workspace, term="First Oath", category="history", canon_state="disputed"
    )
    csource, ctarget = sorted((canon, disputed), key=lambda item: item.id)
    CodexRelation.objects.create(workspace=workspace, source=csource, target=ctarget)
    with pytest.raises(IntegrityError):
        CodexRelation.objects.create(workspace=workspace, source=csource, target=ctarget)


def test_item_creature_character_and_world_links() -> None:
    _, workspace, _ = owner()
    character = Character.objects.create(workspace=workspace, name="Mara")
    group = CharacterGroup.objects.create(workspace=workspace, name="Wardens", group_type="order")
    location = Location.objects.create(
        workspace=workspace, name="Deep Gate", location_type="landmark"
    )
    codex = CodexEntry.objects.create(workspace=workspace, term="Gate Law", category="law")
    item = WorldItem.objects.create(
        workspace=workspace, name="Black Key", item_type="key_item", current_location=location
    )
    creature = Creature.objects.create(
        workspace=workspace, name="Bell Eater", creature_type="individual", threat_level="severe"
    )
    LocationCharacterLink.objects.create(
        workspace=workspace, location=location, character=character, role="home"
    )
    CodexCharacterLink.objects.create(workspace=workspace, codex=codex, character=character)
    CreatureCharacterLink.objects.create(
        workspace=workspace, creature=creature, character=character, role="hunted"
    )
    CreatureGroupLink.objects.create(
        workspace=workspace, creature=creature, group=group, role="worshipped_by"
    )
    CreatureLocationLink.objects.create(workspace=workspace, creature=creature, location=location)
    CreatureCodexLink.objects.create(workspace=workspace, creature=creature, codex=codex)
    assert item.current_location == location
    assert character.locationcharacterlink_links.get().role == "home"
    with pytest.raises(IntegrityError):
        LocationCharacterLink.objects.create(
            workspace=workspace, location=location, character=character
        )


def test_scene_context_archived_read_only_chapter_derivation_dashboard_and_search() -> None:
    account, workspace, client = owner()
    work = Work.objects.create(
        workspace=workspace, title="World Work", work_type="novel", status="drafting"
    )
    chapter = Chapter.objects.create(workspace=workspace, work=work, title="Crossing", order=1)
    result = create_scene(actor=account, workspace_id=workspace.id, title="At the Gate")
    scene = result.scene
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        values={
            "work": work,
            "volume": None,
            "arc": None,
            "chapter": chapter,
            "structure_order": 1,
        },
    )
    location = Location.objects.create(workspace=workspace, name="Gate", location_type="landmark")
    item = WorldItem.objects.create(workspace=workspace, name="Key", item_type="key_item")
    creature = Creature.objects.create(workspace=workspace, name="Watcher", creature_type="monster")
    url = reverse("scene-world-context-update", args=(scene.id,))
    assert client.get(url).status_code == 405
    response = client.post(
        url,
        {
            "primary_location": location.id,
            "locations": [location.id],
            "items": [item.id],
            "creatures": [creature.id],
        },
    )
    assert response.status_code == 302
    assert SceneLocationLink.objects.get(scene=scene).role == "primary"
    summary = summarize_chapter(chapter)
    assert (
        summary.locations == (location,)
        and summary.items == (item,)
        and summary.creatures == (creature,)
    )
    Scene.objects.filter(id=scene.id).update(lifecycle=Scene.Lifecycle.ARCHIVED)
    assert client.post(url, {"locations": []}).status_code == 404
    dashboard = client.get(reverse("workspace-home"))
    assert b"Worldbuilding" in dashboard.content and b"1 places" in dashboard.content
    search = client.post(reverse("scene-search"), {"query": "Watcher", "include_archived": ""})
    assert b"Creatures" in search.content and b"Watcher" in search.content
