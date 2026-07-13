import os
from typing import cast

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.forms import CharacterCreateForm
from characters.models import Character, CharacterScene
from characters.search import SEARCH_FIELDS, search_characters
from scenes.models import Scene
from scenes.services import create_scene
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

TEST_PASSWORD = "Synthetic-Character-Password-Only!"


def _owner(email: str = "character-owner@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=TEST_PASSWORD)
    workspace = cast(Workspace, Workspace.objects.create(name="Synthetic Character Workspace"))
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _client(account: Account) -> Client:
    client = Client()
    client.force_login(account)
    return client


def _character(workspace: Workspace, name: str = "Mara Venn", **values: str) -> Character:
    defaults = {
        "aliases": "The Cartographer\nM. Venn",
        "role": "Protagonist",
        "status": "Missing",
        "summary": "Maps vanished roads.",
        "appearance": "Ink-stained hands.",
        "personality": "Patient until cornered.",
        "goals": "Find the road home.",
        "internal_conflict": "Fears being remembered incorrectly.",
        "external_conflict": "The archive is hunting her.",
        "voice_notes": "Precise, dry, and rarely direct.",
        "notes": "Keeps every broken compass.",
    }
    defaults.update(values)
    return cast(Character, Character.objects.create(workspace=workspace, name=name, **defaults))


def _scene(account: Account, workspace: Workspace, title: str = "The Glass Archive") -> Scene:
    return create_scene(
        actor=account,
        workspace_id=workspace.id,
        title=title,
        ordering=None,
    ).scene


def _dossier_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "name": "Mara Venn",
        "aliases": "The Cartographer\nM. Venn",
        "role": "Protagonist",
        "status": "Missing",
        "summary": "Maps vanished roads.",
        "appearance": "Ink-stained hands.",
        "personality": "Patient until cornered.",
        "goals": "Find the road home.",
        "internal_conflict": "Fears being remembered incorrectly.",
        "external_conflict": "The archive is hunting her.",
        "voice_notes": "Precise and dry.",
        "notes": "Keeps every broken compass.",
    }
    payload.update(overrides)
    return payload


def test_character_creation_is_scoped_normalized_and_redirects_to_dossier() -> None:
    account, workspace = _owner()
    response = _client(account).post(
        reverse("character-create"),
        {
            "name": "  Mara Venn  ",
            "aliases": " The Cartographer \n\nM. Venn\nthe cartographer",
            "role": "Protagonist",
            "status": "New arrival",
            "summary": "Maps vanished roads.",
        },
    )
    assert response.status_code == 303
    character = Character.objects.get()
    assert character.workspace == workspace
    assert character.name == "Mara Venn"
    assert character.alias_list == ("The Cartographer", "M. Venn")
    assert response.url == reverse("character-detail", kwargs={"character_id": character.id})


def test_character_validation_requires_name_and_bounds_optional_status() -> None:
    form = CharacterCreateForm(
        {"name": "   ", "aliases": "", "role": "", "status": "x" * 121, "summary": ""}
    )
    assert not form.is_valid()
    assert "name" in form.errors
    assert "status" in form.errors

    invalid = Character(name="   ")
    with pytest.raises(ValidationError):
        invalid.full_clean(
            exclude=("workspace",), validate_unique=False, validate_constraints=False
        )


def test_character_list_has_private_empty_state_and_complete_cards() -> None:
    account, workspace = _owner()
    client = _client(account)
    assert Client().get(reverse("character-list")).status_code == 302
    empty = client.get(reverse("character-list"))
    assert empty.status_code == 200
    assert b"No Characters yet" in empty.content
    assert b"Create your first Character" in empty.content
    assert "no-store" in empty.headers["Cache-Control"]

    character = _character(workspace)
    response = client.get(reverse("character-list"))
    for value in (
        character.name,
        "The Cartographer",
        character.role,
        character.status,
        character.summary,
        "Updated",
    ):
        assert value.encode() in response.content


def test_character_detail_edits_full_dossier_and_escapes_content() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    client = _client(account)
    detail_url = reverse("character-detail", kwargs={"character_id": character.id})
    response = client.get(detail_url)
    assert response.status_code == 200
    assert b"Character dossier" in response.content
    assert b"Desire and pressure" in response.content
    assert "no-store" in response.headers["Cache-Control"]

    updated = _dossier_payload(
        name="Mara Vale",
        personality="<script>observant</script>",
        notes="A new private note.",
    )
    saved = client.post(detail_url, updated)
    assert saved.status_code == 303
    character.refresh_from_db()
    assert character.name == "Mara Vale"
    assert character.personality == "<script>observant</script>"
    rendered = client.get(detail_url)
    assert b"&lt;script&gt;observant&lt;/script&gt;" in rendered.content
    assert b"<script>observant</script>" not in rendered.content


def test_character_views_and_search_do_not_leak_other_workspaces() -> None:
    account, workspace = _owner()
    other_account, other_workspace = _owner("other-character-owner@example.invalid")
    own = _character(workspace, name="Visible Character")
    other = _character(other_workspace, name="Hidden Character", summary="Needle phrase")
    client = _client(account)

    listing = client.get(reverse("character-list"))
    assert own.name.encode() in listing.content
    assert other.name.encode() not in listing.content
    assert (
        client.get(reverse("character-detail", kwargs={"character_id": other.id})).status_code
        == 404
    )
    assert (
        search_characters(actor=account, workspace_id=workspace.id, query_text="Needle phrase")
        == []
    )
    del other_account


def test_character_scene_linking_unlinking_and_backlinks() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    scene = _scene(account, workspace)
    client = _client(account)
    detail_url = reverse("character-detail", kwargs={"character_id": character.id})

    linked = client.post(
        reverse("character-scene-link", kwargs={"character_id": character.id}),
        {"scene": scene.id},
    )
    assert linked.status_code == 303
    assert CharacterScene.objects.filter(character=character, scene=scene).exists()
    detail = client.get(detail_url)
    assert scene.title.encode() in detail.content
    assert reverse("scene-editor", kwargs={"scene_id": scene.id}).encode() in detail.content
    editor = client.get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert character.name.encode() in editor.content
    assert reverse("character-detail", kwargs={"character_id": character.id}).encode() in (
        editor.content
    )

    unlinked = client.post(
        reverse(
            "character-scene-unlink",
            kwargs={"character_id": character.id, "scene_id": scene.id},
        )
    )
    assert unlinked.status_code == 303
    assert not CharacterScene.objects.filter(character=character, scene=scene).exists()


def test_scene_selector_replaces_links_and_rejects_cross_workspace_character() -> None:
    account, workspace = _owner()
    first = _character(workspace, name="First Character")
    second = _character(workspace, name="Second Character")
    scene = _scene(account, workspace)
    other_account, other_workspace = _owner("selector-other@example.invalid")
    other = _character(other_workspace, name="Other Character")
    client = _client(account)
    selector_url = reverse("scene-characters-update", kwargs={"scene_id": scene.id})

    assert client.post(selector_url, {"characters": [first.id, second.id]}).status_code == 303
    assert set(scene.characters.values_list("id", flat=True)) == {first.id, second.id}
    assert client.post(selector_url, {"characters": [second.id]}).status_code == 303
    assert set(scene.characters.values_list("id", flat=True)) == {second.id}
    assert client.post(selector_url, {"characters": [other.id]}).status_code == 404
    assert set(scene.characters.values_list("id", flat=True)) == {second.id}
    del other_account


def test_archived_scene_keeps_character_links_visible_and_read_only() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    scene = _scene(account, workspace)
    CharacterScene.objects.create(workspace=workspace, character=character, scene=scene)
    Scene.objects.filter(id=scene.id).update(lifecycle=Scene.Lifecycle.ARCHIVED)
    client = _client(account)

    editor = client.get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert editor.status_code == 200
    assert character.name.encode() in editor.content
    assert b"Archived Scene relationships are read-only." in editor.content
    assert b"Save Characters" not in editor.content

    selector = client.post(
        reverse("scene-characters-update", kwargs={"scene_id": scene.id}),
        {"characters": []},
    )
    unlink = client.post(
        reverse(
            "character-scene-unlink",
            kwargs={"character_id": character.id, "scene_id": scene.id},
        )
    )
    assert selector.status_code == 404
    assert unlink.status_code == 404
    assert CharacterScene.objects.filter(character=character, scene=scene).exists()

    dossier = client.get(reverse("character-detail", kwargs={"character_id": character.id}))
    assert scene.title.encode() in dossier.content
    assert reverse("scene-editor", kwargs={"scene_id": scene.id}).encode() in dossier.content
    assert b"Unlink" not in dossier.content


def test_character_scene_model_rejects_cross_workspace_link() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    other_account, other_workspace = _owner("link-other@example.invalid")
    other_scene = _scene(other_account, other_workspace, "Other Scene")
    link = CharacterScene(workspace=workspace, character=character, scene=other_scene)
    with pytest.raises(ValidationError):
        link.full_clean()
    assert CharacterScene.objects.count() == 0
    del account


@pytest.mark.parametrize("field", SEARCH_FIELDS)
def test_character_search_covers_every_approved_dossier_field(field: str) -> None:
    account, workspace = _owner(email=f"search-{field}@example.invalid")
    values = {name: "" for name in SEARCH_FIELDS if name not in {"name", "status"}}
    values[field] = "Cobalt lantern"
    name = values.pop("name", "Search Subject") or "Search Subject"
    character = _character(workspace, name=name, **values)

    results = search_characters(
        actor=account,
        workspace_id=workspace.id,
        query_text="Cobalt lantern",
    )
    assert [result.character for result in results] == [character]
    assert "Cobalt lantern" in results[0].snippet


def test_combined_search_labels_character_results_separately() -> None:
    account, workspace = _owner()
    character = _character(workspace, summary="Carries the cobalt lantern.")
    response = _client(account).post(reverse("scene-search"), {"query": "cobalt lantern"})
    assert response.status_code == 200
    assert b"Characters" in response.content
    assert b"Character" in response.content
    assert character.name.encode() in response.content
    assert reverse("character-detail", kwargs={"character_id": character.id}).encode() in (
        response.content
    )


def test_dashboard_includes_workspace_character_count_and_recent_character() -> None:
    account, workspace = _owner()
    older = _character(workspace, name="Older Character")
    recent = _character(workspace, name="Recent Character")
    response = _client(account).get(reverse("workspace-home"))
    assert response.status_code == 200
    assert response.context["character_count"] == 2
    assert list(response.context["recent_characters"]) == [recent, older]
    assert b"Characters" in response.content
    assert recent.name.encode() in response.content
    assert reverse("character-detail", kwargs={"character_id": recent.id}).encode() in (
        response.content
    )
