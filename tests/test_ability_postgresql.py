import os
import re
from datetime import date
from typing import cast

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Ability, AbilityEvent, AbilityPrediction, AbilityStage, Character
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

TEST_PASSWORD = "Synthetic-Ability-Password-Only!"


def _owner(email: str = "ability-owner@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=TEST_PASSWORD)
    workspace = cast(Workspace, Workspace.objects.create(name="Synthetic Ability Workspace"))
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _client(account: Account, *, csrf: bool = False) -> Client:
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(account)
    return client


def _character(workspace: Workspace, name: str = "Mara Venn") -> Character:
    return cast(
        Character,
        Character.objects.create(
            workspace=workspace,
            name=name,
            summary="Maps vanished roads.",
        ),
    )


def _ability(workspace: Workspace, character: Character, name: str = "Roadsense") -> Ability:
    return cast(
        Ability,
        Ability.objects.create(
            workspace=workspace,
            character=character,
            name=name,
            category="Cartomancy",
            description="Finds roads the world has forgotten.",
            limitations="Cannot find a road deliberately destroyed.",
            costs="Forgets one familiar place after each use.",
            mastery=Ability.Mastery.TRAINED,
            status=Ability.Status.ACTIVE,
            notes="Works best near old boundary stones.",
        ),
    )


def _scene(account: Account, workspace: Workspace, title: str = "The Glass Archive") -> Scene:
    return create_scene(
        actor=account,
        workspace_id=workspace.id,
        title=title,
        ordering=None,
    ).scene


def _ability_url(character: Character, ability: Ability) -> str:
    return reverse(
        "ability-detail",
        kwargs={"character_id": character.id, "ability_id": ability.id},
    )


def _ability_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "name": "Roadsense",
        "category": "Cartomancy",
        "description": "Finds roads the world has forgotten.",
        "limitations": "Cannot find a road deliberately destroyed.",
        "costs": "Forgets one familiar place after each use.",
        "mastery": Ability.Mastery.TRAINED,
        "status": Ability.Status.ACTIVE,
        "notes": "Works best near old boundary stones.",
    }
    payload.update(overrides)
    return payload


def test_dossier_has_ability_empty_state_creation_and_summary() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    client = _client(account)
    dossier_url = reverse("character-detail", kwargs={"character_id": character.id})
    empty = client.get(dossier_url)
    assert empty.status_code == 200
    assert empty.context["ability_count"] == 0
    assert b"No Abilities recorded yet" in empty.content

    created = client.post(
        reverse("ability-create", kwargs={"character_id": character.id}),
        _ability_payload(
            name="  Roadsense  ",
            category="",
            description="",
            limitations="",
            costs="",
            mastery=Ability.Mastery.EMERGING,
            status=Ability.Status.ACTIVE,
            notes="",
        ),
    )
    assert created.status_code == 303
    ability = Ability.objects.get()
    assert ability.name == "Roadsense"
    dossier = client.get(dossier_url)
    assert dossier.context["ability_count"] == 1
    assert dossier.context["active_ability_count"] == 1
    assert b"Roadsense" in dossier.content
    assert b"Emerging" in dossier.content


def test_ability_required_validation_preserves_values_and_edit_delete_are_explicit() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    client = _client(account)
    create_url = reverse("ability-create", kwargs={"character_id": character.id})
    invalid = client.post(create_url, _ability_payload(name="   ", category="Arcane craft"))
    assert invalid.status_code == 422
    assert b"This field is required" in invalid.content
    assert b"Arcane craft" in invalid.content

    edited = client.post(
        _ability_url(character, ability),
        _ability_payload(name="Roadsense refined", mastery=Ability.Mastery.ADVANCED),
    )
    assert edited.status_code == 303
    ability.refresh_from_db()
    assert ability.name == "Roadsense refined"
    assert ability.mastery == Ability.Mastery.ADVANCED

    delete_url = reverse(
        "ability-delete",
        kwargs={"character_id": character.id, "ability_id": ability.id},
    )
    confirmation = client.get(delete_url)
    assert confirmation.status_code == 200
    assert b"This also removes its progression records" in confirmation.content
    assert client.post(delete_url).status_code == 303
    assert not Ability.objects.filter(id=ability.id).exists()


def test_ability_cards_show_mastery_status_current_stage_and_long_text_safely() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character, name="A" * 200)
    Ability.objects.filter(id=ability.id).update(
        description="B" * 4000,
        status=Ability.Status.UNSTABLE,
        mastery=Ability.Mastery.MASTERED,
    )
    _ability(workspace, character, name="Echo speech")
    Ability.objects.create(
        workspace=workspace,
        character=character,
        name="Unclassified instinct",
        category="",
        description="",
        limitations="",
        costs="",
        mastery=Ability.Mastery.LATENT,
        status=Ability.Status.DORMANT,
        notes="",
    )
    AbilityStage.objects.create(
        workspace=workspace,
        ability=ability,
        name="Threshold Sight",
        order=2,
        state=AbilityStage.State.CURRENT,
    )
    response = _client(account).get(
        reverse("character-detail", kwargs={"character_id": character.id})
    )
    assert response.context["ability_count"] == 3
    assert response.context["active_ability_count"] == 1
    assert response.context["current_stage_count"] == 1
    for text in (b"Mastered", b"Unstable", b"Threshold Sight", b"Current stage"):
        assert text in response.content


def test_stage_ordering_and_moving_current_stage_are_atomic() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    client = _client(account)
    create_url = reverse(
        "ability-stage-create",
        kwargs={"character_id": character.id, "ability_id": ability.id},
    )
    assert (
        client.post(
            create_url,
            {
                "name": "First awakening",
                "order": 10,
                "state": AbilityStage.State.CURRENT,
                "description": "Hears the nearest lost road.",
                "requirements": "Survive being lost.",
                "costs": "Disorientation.",
            },
        ).status_code
        == 303
    )
    first = AbilityStage.objects.get(name="First awakening")
    assert (
        client.post(
            create_url,
            {
                "name": "Deliberate navigation",
                "order": 20,
                "state": AbilityStage.State.CURRENT,
                "description": "Chooses among forgotten roads.",
                "requirements": "Map a place from memory.",
                "costs": "Memory erosion.",
            },
        ).status_code
        == 303
    )
    first.refresh_from_db()
    second = AbilityStage.objects.get(name="Deliberate navigation")
    assert first.state == AbilityStage.State.PAST
    assert second.state == AbilityStage.State.CURRENT

    AbilityStage.objects.create(
        workspace=workspace,
        ability=ability,
        name="Rejected shortcut",
        order=30,
        state=AbilityStage.State.REJECTED,
    )
    AbilityStage.objects.create(
        workspace=workspace,
        ability=ability,
        name="Possible crossing",
        order=40,
        state=AbilityStage.State.POSSIBLE,
    )
    response = client.get(_ability_url(character, ability))
    assert [stage.name for stage in response.context["stages"]] == [
        "First awakening",
        "Deliberate navigation",
        "Rejected shortcut",
        "Possible crossing",
    ]
    assert b"Current now" in response.content

    with pytest.raises(IntegrityError), transaction.atomic():
        AbilityStage.objects.create(
            workspace=workspace,
            ability=ability,
            name="Conflicting current",
            order=50,
            state=AbilityStage.State.CURRENT,
        )


def test_progression_events_are_newest_first_and_link_to_scene_editor() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    scene = _scene(account, workspace)
    client = _client(account)
    create_url = reverse(
        "ability-event-create",
        kwargs={"character_id": character.id, "ability_id": ability.id},
    )
    assert (
        client.post(
            create_url,
            {
                "title": "First map opened",
                "event_type": AbilityEvent.EventType.AWAKENING,
                "event_date": "2024-01-02",
                "story_time": "Before the archive",
                "description": "The road answered once.",
                "scene": "",
            },
        ).status_code
        == 303
    )
    linked = client.post(
        create_url,
        {
            "title": "Archive breakthrough",
            "event_type": AbilityEvent.EventType.BREAKTHROUGH,
            "event_date": "2025-02-03",
            "story_time": "Act II",
            "description": "The road answered by name.",
            "scene": scene.id,
        },
    )
    assert linked.status_code == 303, linked.context["form"].errors.as_json()
    response = client.get(_ability_url(character, ability))
    body = response.content.decode()
    assert body.index("Archive breakthrough") < body.index("First map opened")
    assert reverse("scene-editor", kwargs={"scene_id": scene.id}) in body
    assert AbilityEvent.objects.get(title="Archive breakthrough").event_date == date(2025, 2, 3)
    editor = client.get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert b"Ability progression" in editor.content
    assert b"Archive breakthrough" in editor.content
    assert _ability_url(character, ability).encode() in editor.content


def test_event_scene_choices_reject_cross_workspace_and_allow_no_scene() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    other_account, other_workspace = _owner("ability-other@example.invalid")
    other_scene = _scene(other_account, other_workspace, "Hidden Scene")
    client = _client(account)
    create_url = reverse(
        "ability-event-create",
        kwargs={"character_id": character.id, "ability_id": ability.id},
    )
    rejected = client.post(
        create_url,
        {
            "title": "Crossed boundary",
            "event_type": AbilityEvent.EventType.DISCOVERY,
            "event_date": "",
            "story_time": "",
            "description": "Synthetic only.",
            "scene": other_scene.id,
        },
    )
    assert rejected.status_code == 422
    assert not AbilityEvent.objects.exists()
    allowed = client.post(
        create_url,
        {
            "title": "Unplaced discovery",
            "event_type": AbilityEvent.EventType.DISCOVERY,
            "event_date": "",
            "story_time": "Between chapters",
            "description": "Synthetic only.",
            "scene": "",
        },
    )
    assert allowed.status_code == 303
    assert AbilityEvent.objects.get().scene is None


def test_archived_scene_event_link_stays_readable_and_cannot_be_newly_selected() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    scene = _scene(account, workspace)
    event = AbilityEvent.objects.create(
        workspace=workspace,
        ability=ability,
        title="The archive closed",
        event_type=AbilityEvent.EventType.LOSS,
        scene=scene,
    )
    Scene.objects.filter(id=scene.id).update(lifecycle=Scene.Lifecycle.ARCHIVED)
    client = _client(account)
    detail = client.get(_ability_url(character, ability))
    assert "Archived · read-only".encode() in detail.content
    assert scene.title.encode() in detail.content

    edit_url = reverse(
        "ability-event-edit",
        kwargs={
            "character_id": character.id,
            "ability_id": ability.id,
            "event_id": event.id,
        },
    )
    assert (
        client.post(
            edit_url,
            {
                "title": "The archive closed",
                "event_type": AbilityEvent.EventType.LOSS,
                "event_date": "",
                "story_time": "Act III",
                "description": "The existing link remains readable.",
                "scene": scene.id,
            },
        ).status_code
        == 303
    )
    event.refresh_from_db()
    assert event.scene == scene

    second = _ability(workspace, character, "Echo speech")
    rejected = client.post(
        reverse(
            "ability-event-create",
            kwargs={"character_id": character.id, "ability_id": second.id},
        ),
        {
            "title": "Unsafe new archive link",
            "event_type": AbilityEvent.EventType.DISCOVERY,
            "event_date": "",
            "story_time": "",
            "description": "",
            "scene": scene.id,
        },
    )
    assert rejected.status_code == 422
    assert not AbilityEvent.objects.filter(ability=second).exists()


@pytest.mark.parametrize(
    "status,label",
    [
        (AbilityPrediction.Status.ACTIVE, "Active"),
        (AbilityPrediction.Status.CAME_TRUE, "Came true"),
        (AbilityPrediction.Status.DIVERGED, "Diverged"),
        (AbilityPrediction.Status.DISMISSED, "Dismissed"),
    ],
)
def test_predictions_are_editable_and_visibly_speculative(status: str, label: str) -> None:
    account, workspace = _owner(email=f"prediction-{status}@example.invalid")
    character = _character(workspace)
    ability = _ability(workspace, character)
    client = _client(account)
    create_url = reverse(
        "ability-prediction-create",
        kwargs={"character_id": character.id, "ability_id": ability.id},
    )
    created = client.post(
        create_url,
        {
            "title": "A possible endgame",
            "prediction": "Might open a road between memories.",
            "rationale": "The existing limitation points there.",
            "status": status,
            "notes": "Private synthetic note.",
        },
    )
    assert created.status_code == 303
    prediction = AbilityPrediction.objects.get()
    detail = client.get(_ability_url(character, ability))
    for text in ("Private speculation", "Not canon", label, prediction.prediction):
        assert text.encode() in detail.content

    edit_url = reverse(
        "ability-prediction-edit",
        kwargs={
            "character_id": character.id,
            "ability_id": ability.id,
            "prediction_id": prediction.id,
        },
    )
    assert (
        client.post(
            edit_url,
            {
                "title": prediction.title,
                "prediction": prediction.prediction,
                "rationale": prediction.rationale,
                "status": AbilityPrediction.Status.DIVERGED,
                "notes": prediction.notes,
            },
        ).status_code
        == 303
    )
    prediction.refresh_from_db()
    assert prediction.status == AbilityPrediction.Status.DIVERGED


def test_ability_views_are_workspace_scoped_without_leakage() -> None:
    account, workspace = _owner()
    character = _character(workspace, "Visible Character")
    ability = _ability(workspace, character, "Visible Ability")
    other_account, other_workspace = _owner("hidden-ability@example.invalid")
    other_character = _character(other_workspace, "Hidden Character")
    other_ability = _ability(other_workspace, other_character, "Hidden Ability")
    client = _client(account)

    assert client.get(_ability_url(character, ability)).status_code == 200
    assert client.get(_ability_url(other_character, other_ability)).status_code == 404
    assert (
        client.get(
            reverse("ability-create", kwargs={"character_id": other_character.id})
        ).status_code
        == 404
    )
    dossier = client.get(reverse("character-detail", kwargs={"character_id": character.id}))
    assert b"Visible Ability" in dossier.content
    assert b"Hidden Ability" not in dossier.content


def test_model_validation_rejects_cross_workspace_children() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    other_account, other_workspace = _owner("model-other@example.invalid")
    other_scene = _scene(other_account, other_workspace)

    event = AbilityEvent(
        workspace=workspace,
        ability=ability,
        title="Invalid event",
        scene=other_scene,
    )
    with pytest.raises(ValidationError):
        event.full_clean()
    foreign_stage = AbilityStage(
        workspace=other_workspace,
        ability=ability,
        name="Invalid stage",
        order=1,
    )
    with pytest.raises(ValidationError):
        foreign_stage.full_clean()


def test_child_deletes_are_post_only_and_csrf_protected() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    stage = AbilityStage.objects.create(
        workspace=workspace,
        ability=ability,
        name="Temporary stage",
        order=1,
    )
    delete_url = reverse(
        "ability-stage-delete",
        kwargs={
            "character_id": character.id,
            "ability_id": ability.id,
            "stage_id": stage.id,
        },
    )
    client = _client(account)
    assert client.get(delete_url).status_code == 405
    assert _client(account, csrf=True).post(delete_url).status_code == 403
    assert AbilityStage.objects.filter(id=stage.id).exists()
    assert client.post(delete_url).status_code == 303
    assert not AbilityStage.objects.filter(id=stage.id).exists()


def test_authenticated_ability_forms_have_unique_ids_and_associated_labels() -> None:
    account, workspace = _owner()
    character = _character(workspace)
    ability = _ability(workspace, character)
    client = _client(account)
    urls = (
        reverse("ability-create", kwargs={"character_id": character.id}),
        reverse(
            "ability-stage-create",
            kwargs={"character_id": character.id, "ability_id": ability.id},
        ),
        reverse(
            "ability-event-create",
            kwargs={"character_id": character.id, "ability_id": ability.id},
        ),
        reverse(
            "ability-prediction-create",
            kwargs={"character_id": character.id, "ability_id": ability.id},
        ),
    )
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        html = response.content.decode()
        identifiers = re.findall(r'\bid="([^"]+)"', html)
        assert len(identifiers) == len(set(identifiers))
        for field in response.context["form"]:
            assert f'id="{field.id_for_label}"' in html
            assert f'for="{field.id_for_label}"' in html
