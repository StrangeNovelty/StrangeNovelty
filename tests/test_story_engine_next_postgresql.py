import os

import pytest
from django.test import Client, override_settings

from accounts.models import Account
from ai_assistance.models import BrainstormSession
from characters.models import (
    Ability,
    Character,
    CharacterMechanicMembership,
    CustomMechanicTemplate,
)
from decks.models import Deck, DeckCard, DeckCategory
from stories.models import Work
from story_engine_next.models import BrainstormCardSelection, WorldBibleEntry
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_domain(email="next@example.invalid"):
    account = Account.objects.create_user(email, password="Synthetic-Only!")
    workspace = Workspace.objects.create(name="Synthetic Browser Port")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Serial", work_type="web_serial"
    )
    Character.objects.create(workspace=workspace, name="Synthetic Navigator")
    deck = Deck.objects.create(
        workspace=workspace, name="Synthetic Cards", source_identity="synthetic-cards"
    )
    category = DeckCategory.objects.create(
        deck=deck, name="Synthetic Category", source_identity="synthetic-category"
    )
    for index in range(12):
        DeckCard.objects.create(
            deck=deck,
            category=category,
            stable_source_identity=f"synthetic-{index}",
            title=f"Synthetic Card {index}",
            prompt=f"Synthetic prompt {index}",
            import_checksum=f"{index:064x}",
        )
    return workspace, client, work


def test_isolated_shell_and_brainstorm_default_to_active_work():
    workspace, client, work = setup_domain()
    assert client.get("/story-engine-next/dashboard").status_code == 200
    created = client.post(
        "/api/story-engine-next/brainstorm/",
        data='{"mode":"plot"}',
        content_type="application/json",
    )
    assert created.status_code == 201
    session = BrainstormSession.objects.get(workspace=workspace)
    assert session.work == work
    assert session.context_pack.work == work


def test_draw_contract_supports_desktop_counts_and_optional_categories():
    workspace, client, _ = setup_domain("draw-next@example.invalid")
    session_id = client.post(
        "/api/story-engine-next/brainstorm/",
        data='{"mode":"realm"}',
        content_type="application/json",
    ).json()["id"]
    for count in (3, 5, 7, 10):
        response = client.post(
            f"/api/story-engine-next/brainstorm/{session_id}/draw/",
            data=f'{{"count":{count},"categories":[]}}',
            content_type="application/json",
        )
        assert response.status_code == 200
        assert len(response.json()["cards"]) == count
        assert BrainstormCardSelection.objects.filter(session_id=session_id).count() == count
    assert BrainstormSession.objects.get(id=session_id).workspace == workspace


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True, AI_MODEL="")
def test_generate_stays_in_workspace_and_persists_result():
    workspace, client, _ = setup_domain("generate-next@example.invalid")
    session_id = client.post(
        "/api/story-engine-next/brainstorm/",
        data='{"mode":"monster"}',
        content_type="application/json",
    ).json()["id"]
    client.post(
        f"/api/story-engine-next/brainstorm/{session_id}/cards/",
        data='{"text":"Synthetic pressure"}',
        content_type="application/json",
    )
    generated = client.post(f"/api/story-engine-next/brainstorm/{session_id}/generate/")
    assert generated.status_code == 200
    assert generated.json()["result"]
    session = BrainstormSession.objects.get(id=session_id)
    assert session.latest_suggestion.workspace == workspace


def test_other_workspace_cannot_open_session():
    workspace, client, _ = setup_domain("owner-next@example.invalid")
    session_id = client.post(
        "/api/story-engine-next/brainstorm/",
        data='{"mode":"plot"}',
        content_type="application/json",
    ).json()["id"]
    del workspace
    _, outsider, _ = setup_domain("outsider-next@example.invalid")
    assert outsider.get(f"/api/story-engine-next/brainstorm/{session_id}/").status_code == 404


def test_sectioned_character_api_updates_only_workspace_character():
    workspace, client, _ = setup_domain("character-next@example.invalid")
    character = workspace.characters.get(name="Synthetic Navigator")
    response = client.patch(
        f"/api/story-engine-next/characters/{character.id}/",
        data='{"personality":"Synthetic reserve and resolve"}',
        content_type="application/json",
    )
    assert response.status_code == 200
    character.refresh_from_db()
    assert character.personality == "Synthetic reserve and resolve"
    _, outsider, _ = setup_domain("character-outsider@example.invalid")
    assert outsider.get(f"/api/story-engine-next/characters/{character.id}/").status_code == 404


def test_world_bible_is_freeform_and_enters_brainstorm_context():
    workspace, client, _ = setup_domain("bible-next@example.invalid")
    created = client.post(
        "/api/story-engine-next/world-bible/",
        data='{"title":"Synthetic physical law"}',
        content_type="application/json",
    )
    entry_id = created.json()["id"]
    client.patch(
        f"/api/story-engine-next/world-bible/{entry_id}/",
        data='{"content":"Promises leave visible synthetic traces."}',
        content_type="application/json",
    )
    entry = WorldBibleEntry.objects.get(id=entry_id, workspace=workspace)
    assert "synthetic traces" in entry.content
    session_id = client.post(
        "/api/story-engine-next/brainstorm/",
        data='{"mode":"plot"}',
        content_type="application/json",
    ).json()["id"]
    with override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True, AI_MODEL=""):
        generated = client.post(f"/api/story-engine-next/brainstorm/{session_id}/generate/")
    assert generated.status_code == 200
    session = BrainstormSession.objects.get(id=session_id)
    assert (
        "Promises leave visible synthetic traces"
        in session.latest_suggestion.request.assembled_context
    )


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True, AI_MODEL="")
def test_reviewed_apply_uses_real_world_bible_and_character_destinations():
    workspace, client, _ = setup_domain("apply-next@example.invalid")
    character = workspace.characters.get(name="Synthetic Navigator")
    session_id = client.post(
        "/api/story-engine-next/brainstorm/",
        data='{"mode":"plot"}',
        content_type="application/json",
    ).json()["id"]
    generated = client.post(f"/api/story-engine-next/brainstorm/{session_id}/generate/").json()
    suggestion_id = generated["result"]["id"]
    applied = client.post(
        f"/api/story-engine-next/suggestions/{suggestion_id}/apply/",
        data='{"destination":"world_bible","title":"Synthetic law","content":"A reviewed rule."}',
        content_type="application/json",
    )
    assert applied.status_code == 200
    assert WorldBibleEntry.objects.filter(
        workspace=workspace, title="Synthetic law", content="A reviewed rule."
    ).exists()

    second_id = client.post(f"/api/story-engine-next/brainstorm/{session_id}/generate/").json()[
        "result"
    ]["id"]
    note = client.post(
        f"/api/story-engine-next/suggestions/{second_id}/apply/",
        data=(
            '{"destination":"character_note","title":"Reviewed note",'
            f'"content":"Synthetic note.","targetId":"{character.id}"}}'
        ),
        content_type="application/json",
    )
    assert note.status_code == 200
    character.refresh_from_db()
    assert "Synthetic note." in character.notes


def test_bio_arcane_borrow_log_is_structured_and_workspace_scoped():
    workspace, client, work = setup_domain("borrow-next@example.invalid")
    borrower = workspace.characters.get(name="Synthetic Navigator")
    source = Character.objects.create(workspace=workspace, name="Synthetic Source")
    ability = Ability.objects.create(workspace=workspace, character=source, name="Synthetic Gift")
    template = CustomMechanicTemplate.objects.create(
        workspace=workspace,
        work=work,
        name="Synthetic Shared Mechanic",
        borrowing_rules="Borrowing has a visible cost.",
    )
    membership = CharacterMechanicMembership.objects.create(
        workspace=workspace,
        character=borrower,
        template=template,
        designation="02",
    )
    created = client.post(
        f"/api/story-engine-next/characters/{borrower.id}/mechanics/{membership.id}/borrow/",
        data=(
            f'{{"borrowedFrom":"{source.id}","ability":"{ability.id}",'
            '"abilityName":"Synthetic Gift","cost":"Synthetic fatigue",'
            '"consequence":"Synthetic recovery"}'
        ),
        content_type="application/json",
    )
    assert created.status_code == 201
    log = membership.borrowing_log.get()
    assert log.borrowed_from == source
    assert log.ability == ability
    assert log.cost_or_damage == "Synthetic fatigue"
    _, outsider, _ = setup_domain("borrow-outsider@example.invalid")
    assert (
        outsider.get(
            f"/api/story-engine-next/characters/{borrower.id}/mechanics/{membership.id}/borrow/"
        ).status_code
        == 404
    )
