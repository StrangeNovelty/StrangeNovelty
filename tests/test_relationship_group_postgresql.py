import os
from typing import cast

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character, CharacterGroup, CharacterRelationship, GroupMembership
from characters.search import search_character_groups
from jobs.services import claim_jobs, execute_claim
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

TEST_PASSWORD = "Synthetic-Connected-Cast-Only!"


def _owner(email: str = "connected-cast-owner@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=TEST_PASSWORD)
    workspace = cast(Workspace, Workspace.objects.create(name="Synthetic Connected Cast"))
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


def _character(workspace: Workspace, name: str) -> Character:
    return cast(Character, Character.objects.create(workspace=workspace, name=name))


def _relationship_payload(other: Character, **overrides: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "other_character": other.id,
        "relationship_type": "complicated",
        "short_label": "Reluctant co-conspirators",
        "summary": "They need one another but disagree about the cost.",
        "current_perspective": "Trusts the plan, not the person.",
        "other_perspective": "Trusts the person, not the plan.",
        "status": "strained",
        "knowledge_state": "secret",
        "notes": "Synthetic relationship notes.",
    }
    payload.update(overrides)
    return payload


def _group_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "name": "The Lantern Crew",
        "group_type": "crew",
        "status": "active",
        "tagline": "Keeps the harbor lights alive.",
        "description": "A test-only group with no private story content.",
        "purpose": "Protect the harbor.",
        "notes": "Synthetic Group notes.",
    }
    payload.update(overrides)
    return payload


def _membership_payload(character: Character, **overrides: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "character": character.id,
        "role": "Navigator",
        "status": "active",
        "rank_label": "Third lantern",
        "joined_story_time": "Before the winter crossing",
        "left_story_time": "",
        "notes": "Synthetic membership notes.",
    }
    payload.update(overrides)
    return payload


def _run_all_jobs() -> None:
    while claimed := claim_jobs(worker_id="connected-cast-test-worker", batch_size=20):
        for item in claimed:
            execute_claim(item)


def test_relationship_creation_is_canonical_asymmetric_and_visible_on_both_dossiers() -> None:
    account, workspace = _owner()
    first = _character(workspace, "Mara Venn")
    second = _character(workspace, "Ivo Reed")
    client = _client(account)

    empty = client.get(reverse("character-detail", kwargs={"character_id": first.id}))
    assert b"No relationships recorded yet" in empty.content

    response = client.post(
        reverse("character-relationship-create", kwargs={"character_id": first.id}),
        _relationship_payload(second),
    )
    assert response.status_code == 303
    relationship = CharacterRelationship.objects.get()
    assert relationship.source_id < relationship.target_id
    expected = {
        first.id: "Trusts the plan, not the person.",
        second.id: "Trusts the person, not the plan.",
    }
    assert {
        relationship.source_id: relationship.source_perspective,
        relationship.target_id: relationship.target_perspective,
    } == expected
    for character, other, perspective in (
        (first, second, expected[first.id]),
        (second, first, expected[second.id]),
    ):
        dossier = client.get(reverse("character-detail", kwargs={"character_id": character.id}))
        assert other.name.encode() in dossier.content
        assert perspective.encode() in dossier.content
        assert b"Complicated" in dossier.content
        assert b"Strained" in dossier.content


def test_relationship_rejects_self_duplicate_and_cross_workspace_characters() -> None:
    account, workspace = _owner()
    first = _character(workspace, "First")
    second = _character(workspace, "Second")
    _, other_workspace = _owner("connected-cast-other@example.invalid")
    outsider = _character(other_workspace, "Outsider")
    client = _client(account)
    url = reverse("character-relationship-create", kwargs={"character_id": first.id})

    assert client.post(url, _relationship_payload(first)).status_code == 422
    assert client.post(url, _relationship_payload(outsider)).status_code == 422
    assert client.post(url, _relationship_payload(second)).status_code == 303
    assert client.post(url, _relationship_payload(second)).status_code == 422
    assert CharacterRelationship.objects.count() == 1


def test_relationship_can_be_edited_from_either_side_and_deleted_after_confirmation() -> None:
    account, workspace = _owner()
    first = _character(workspace, "First")
    second = _character(workspace, "Second")
    client = _client(account)
    client.post(
        reverse("character-relationship-create", kwargs={"character_id": first.id}),
        _relationship_payload(second),
    )
    relationship = CharacterRelationship.objects.get()
    edit_url = reverse(
        "character-relationship-edit",
        kwargs={"character_id": second.id, "relationship_id": relationship.id},
    )
    assert (
        client.post(
            edit_url,
            _relationship_payload(
                first,
                current_perspective="Second now leads.",
                other_perspective="First reluctantly follows.",
                status="historical",
            ),
        ).status_code
        == 303
    )
    relationship.refresh_from_db()
    perspective_by_id = {
        relationship.source_id: relationship.source_perspective,
        relationship.target_id: relationship.target_perspective,
    }
    assert perspective_by_id[second.id] == "Second now leads."
    assert relationship.status == "historical"

    delete_url = reverse(
        "character-relationship-delete",
        kwargs={"character_id": first.id, "relationship_id": relationship.id},
    )
    assert client.get(delete_url).status_code == 200
    assert CharacterRelationship.objects.exists()
    assert client.post(delete_url).status_code == 303
    assert not CharacterRelationship.objects.exists()


def test_group_library_creation_editing_search_and_empty_states() -> None:
    account, workspace = _owner()
    client = _client(account)
    list_url = reverse("character-group-list")
    empty = client.get(list_url)
    assert empty.status_code == 200
    assert b"No Groups yet" in empty.content

    created = client.post(reverse("character-group-create"), _group_payload())
    assert created.status_code == 303
    group = CharacterGroup.objects.get()
    assert group.workspace == workspace
    assert group.name == "The Lantern Crew"
    detail_url = reverse("character-group-detail", kwargs={"group_id": group.id})
    assert client.post(detail_url, _group_payload(status="historical")).status_code == 303
    group.refresh_from_db()
    assert group.status == "historical"
    assert [
        result.group
        for result in search_character_groups(
            actor=account, workspace_id=workspace.id, query_text="harbor"
        )
    ] == [group]
    assert group.name.encode() in client.post(list_url, {"query": "crew"}).content
    assert b"No Groups matched" in client.post(list_url, {"query": "unmatched"}).content


def test_membership_lifecycle_backlinks_and_duplicate_rejection() -> None:
    account, workspace = _owner()
    character = _character(workspace, "Mara Venn")
    client = _client(account)
    client.post(reverse("character-group-create"), _group_payload())
    group = CharacterGroup.objects.get()
    create_url = reverse("group-membership-create", kwargs={"group_id": group.id})

    assert client.post(create_url, _membership_payload(character)).status_code == 303
    assert client.post(create_url, _membership_payload(character)).status_code == 422
    membership = GroupMembership.objects.get()
    group_detail = client.get(reverse("character-group-detail", kwargs={"group_id": group.id}))
    character_detail = client.get(
        reverse("character-detail", kwargs={"character_id": character.id})
    )
    assert character.name.encode() in group_detail.content
    assert group.name.encode() in character_detail.content

    edit_url = reverse(
        "group-membership-edit",
        kwargs={"group_id": group.id, "membership_id": membership.id},
    )
    assert (
        client.post(
            edit_url, _membership_payload(character, status="former", left_story_time="After dawn")
        ).status_code
        == 303
    )
    membership.refresh_from_db()
    assert membership.status == "former"
    assert membership.left_story_time == "After dawn"
    delete_url = reverse(
        "group-membership-delete",
        kwargs={"group_id": group.id, "membership_id": membership.id},
    )
    assert client.get(delete_url).status_code == 405
    assert client.post(delete_url).status_code == 303
    assert not GroupMembership.objects.exists()


def test_membership_rejects_cross_workspace_character_and_group_access() -> None:
    account, workspace = _owner()
    own = _character(workspace, "Own Character")
    other_account, other_workspace = _owner("group-scope-other@example.invalid")
    outsider = _character(other_workspace, "Other Character")
    own_group = CharacterGroup.objects.create(workspace=workspace, **_group_payload())
    other_group = CharacterGroup.objects.create(
        workspace=other_workspace, **_group_payload(name="Other Group")
    )
    client = _client(account)

    own_create = reverse("group-membership-create", kwargs={"group_id": own_group.id})
    assert client.post(own_create, _membership_payload(outsider)).status_code == 422
    assert (
        client.get(
            reverse("character-group-detail", kwargs={"group_id": other_group.id})
        ).status_code
        == 404
    )
    assert other_group.name.encode() not in client.get(reverse("character-group-list")).content
    assert (
        search_character_groups(
            actor=account,
            workspace_id=workspace.id,
            query_text="Other Group",
        )
        == []
    )
    assert not GroupMembership.objects.exists()
    assert (
        own.name.encode()
        not in _client(other_account)
        .get(reverse("character-group-detail", kwargs={"group_id": other_group.id}))
        .content
    )


def test_group_delete_confirmation_cascades_membership_not_character() -> None:
    account, workspace = _owner()
    character = _character(workspace, "Persistent Character")
    group = CharacterGroup.objects.create(workspace=workspace, **_group_payload())
    GroupMembership.objects.create(workspace=workspace, character=character, group=group)
    client = _client(account)
    url = reverse("character-group-delete", kwargs={"group_id": group.id})

    confirmation = client.get(url)
    assert confirmation.status_code == 200
    assert b"1 contained membership" in confirmation.content
    assert client.post(url).status_code == 303
    assert not CharacterGroup.objects.exists()
    assert not GroupMembership.objects.exists()
    assert Character.objects.filter(id=character.id).exists()


def test_character_library_signals_connected_and_unconnected_characters() -> None:
    account, workspace = _owner()
    connected = _character(workspace, "Connected")
    other = _character(workspace, "Other")
    isolated = _character(workspace, "Isolated")
    source, target = sorted((connected, other), key=lambda character: character.id)
    CharacterRelationship.objects.create(
        workspace=workspace,
        source=source,
        target=target,
        relationship_type="friend",
    )
    group = CharacterGroup.objects.create(workspace=workspace, **_group_payload())
    GroupMembership.objects.create(workspace=workspace, character=connected, group=group)

    response = _client(account).get(reverse("character-list"))
    content = response.content.decode()
    assert "1 relationship" in content
    assert "1 Group" in content
    assert "Unconnected" in content
    assert isolated.name in content


def test_combined_search_distinguishes_scene_character_and_group_results() -> None:
    account, workspace = _owner()
    character = _character(workspace, "Lantern Keeper")
    group = CharacterGroup.objects.create(
        workspace=workspace, **_group_payload(name="Lantern Assembly")
    )
    scene = create_scene(
        actor=account,
        workspace_id=workspace.id,
        title="The Lantern Meeting",
        ordering=None,
    ).scene
    _run_all_jobs()
    response = _client(account).post(
        reverse("scene-search"), {"query": "Lantern", "include_archived": ""}
    )
    assert response.status_code == 200
    for heading in (b">Scenes<", b">Characters<", b">Groups<"):
        assert heading in response.content
    assert reverse("scene-editor", kwargs={"scene_id": scene.id}).encode() in response.content
    assert reverse("character-detail", kwargs={"character_id": character.id}).encode() in (
        response.content
    )
    assert reverse("character-group-detail", kwargs={"group_id": group.id}).encode() in (
        response.content
    )


def test_connected_cast_mutations_are_post_only_and_private() -> None:
    account, workspace = _owner()
    first = _character(workspace, "First")
    second = _character(workspace, "Second")
    source, target = sorted((first, second), key=lambda character: character.id)
    relationship = CharacterRelationship.objects.create(
        workspace=workspace,
        source=source,
        target=target,
        relationship_type="ally",
    )
    group = CharacterGroup.objects.create(workspace=workspace, **_group_payload())
    membership = GroupMembership.objects.create(workspace=workspace, character=first, group=group)
    anonymous = Client()
    client = _client(account)
    mutation_urls = (
        reverse(
            "group-membership-delete",
            kwargs={"group_id": group.id, "membership_id": membership.id},
        ),
    )
    for url in mutation_urls:
        assert client.get(url).status_code == 405
        assert anonymous.post(url).status_code == 302
    relationship_delete = reverse(
        "character-relationship-delete",
        kwargs={"character_id": first.id, "relationship_id": relationship.id},
    )
    assert client.get(relationship_delete).status_code == 200
    assert anonymous.post(relationship_delete).status_code == 302
    assert CharacterRelationship.objects.exists()
    assert GroupMembership.objects.exists()


def test_authenticated_qa_renders_varied_cast_states_and_long_content() -> None:
    account, workspace = _owner()
    anchor = _character(workspace, "Anchor Character")
    relatives = [
        _character(workspace, "Family Connection"),
        _character(workspace, "Hidden Rival"),
        _character(workspace, "Historical Ally"),
    ]
    long_token = "unbroken" * 80
    for other, relationship_type, status, knowledge in (
        (relatives[0], "family", "active", "public"),
        (relatives[1], "rival", "broken", "one_sided"),
        (relatives[2], "ally", "historical", "secret"),
    ):
        source, target = sorted((anchor, other), key=lambda character: character.id)
        CharacterRelationship.objects.create(
            workspace=workspace,
            source=source,
            target=target,
            relationship_type=relationship_type,
            short_label=long_token[:160],
            summary=f"{long_token} shared dynamic",
            source_perspective=f"{long_token} source view",
            target_perspective=f"{long_token} target view",
            status=status,
            knowledge_state=knowledge,
        )
    groups = [
        CharacterGroup.objects.create(
            workspace=workspace,
            **_group_payload(name="Synthetic Family", group_type="family"),
        ),
        CharacterGroup.objects.create(
            workspace=workspace,
            **_group_payload(name="Synthetic Team", group_type="team"),
        ),
        CharacterGroup.objects.create(
            workspace=workspace,
            **_group_payload(name="Empty Faction", group_type="faction"),
        ),
    ]
    for group, status in zip(groups[:2], ("active", "hidden"), strict=True):
        GroupMembership.objects.create(
            workspace=workspace,
            character=anchor,
            group=group,
            status=status,
            notes=long_token,
        )
    GroupMembership.objects.create(
        workspace=workspace,
        character=relatives[0],
        group=groups[0],
        status="former",
    )

    client = _client(account)
    dossier = client.get(reverse("character-detail", kwargs={"character_id": anchor.id}))
    assert dossier.status_code == 200
    for value in (
        "Family",
        "Rival",
        "Historical",
        "One-sided",
        "Secret",
        "Synthetic Family",
        "Synthetic Team",
        long_token,
    ):
        assert value.encode() in dossier.content
    for group in groups:
        detail = client.get(reverse("character-group-detail", kwargs={"group_id": group.id}))
        assert detail.status_code == 200
    assert (
        b"No members yet"
        in client.get(reverse("character-group-detail", kwargs={"group_id": groups[2].id})).content
    )
