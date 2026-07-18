import os

import pytest
from django.urls import reverse
from test_character_postgresql import _client, _owner

from ai_assistance.models import AICreativeRequest, AICreativeSuggestion
from characters.forms import BorrowedAbilityLogForm
from characters.models import (
    Ability,
    BorrowedAbilityLog,
    Character,
    CharacterAIFieldProposal,
    CharacterGroup,
    CharacterMechanicMembership,
    CustomMechanicSharedAbility,
    CustomMechanicTemplate,
    GroupMembership,
)
from stories.models import Chapter, Work

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="PostgreSQL required."),
]


def test_character_sections_are_direct_scoped_and_focused():
    account, workspace = _owner("sections@example.invalid")
    character = Character.objects.create(workspace=workspace, name="STAGING QA — Character")
    client = _client(account)
    sections = (
        "overview",
        "appearance",
        "personality",
        "backstory",
        "abilities",
        "relationships",
        "arc-notes",
        "progression",
        "evaluation",
        "appearances",
    )
    for section in sections:
        response = client.get(
            reverse("character-section", kwargs={"character_id": character.id, "section": section})
        )
        assert response.status_code == 200
        assert b'aria-current="page"' in response.content
        assert response.content.count(b'id="character-section-select"') == 1
    assert (
        client.get(
            reverse(
                "character-section", kwargs={"character_id": character.id, "section": "unknown"}
            )
        ).status_code
        == 404
    )
    overview = client.get(
        reverse("character-section", kwargs={"character_id": character.id, "section": "overview"})
    )
    assert b">Bio-Arcane<" not in overview.content
    assert (
        reverse("character-mechanic-setup", kwargs={"character_id": character.id}).encode()
        in overview.content
    )


def test_family_and_custom_mechanic_borrowing_are_structured_and_scoped():
    account, workspace = _owner("mechanic@example.invalid")
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Work", work_type="novel", status="drafting"
    )
    borrower = Character.objects.create(workspace=workspace, name="Borrower")
    source = Character.objects.create(workspace=workspace, name="Source")
    family = CharacterGroup.objects.create(
        workspace=workspace, name="Synthetic Family", group_type="family"
    )
    GroupMembership.objects.create(
        workspace=workspace, character=borrower, group=family, role="Member"
    )
    template = CustomMechanicTemplate.objects.create(
        workspace=workspace,
        work=work,
        name="Synthetic Resonance",
        designation_label="Sequence",
        borrowing_rules="A cost is always recorded.",
    )
    CustomMechanicSharedAbility.objects.create(template=template, name="Shared Sense")
    membership = CharacterMechanicMembership.objects.create(
        workspace=workspace,
        character=borrower,
        template=template,
        family_group=family,
        designation="07",
    )
    ability = Ability.objects.create(workspace=workspace, character=source, name="Source Gift")
    chapter = Chapter.objects.create(
        workspace=workspace, work=work, title="Synthetic Chapter", order=1
    )
    payload = {
        "borrowed_from": source.id,
        "ability": ability.id,
        "ability_name": ability.name,
        "chapter": chapter.id,
        "story_time": "Night one",
        "cost_or_damage": "Temporary exhaustion",
        "duration": "One scene",
        "reduced_effectiveness": "Limited range",
        "limitation_triggered": "No repeat",
        "recovery": "Rest",
        "lasting_consequence": "A visible mark",
        "continuity_implications": "Track recovery",
        "notes": "Synthetic",
    }
    form = BorrowedAbilityLogForm(payload, workspace=workspace, membership=membership)
    assert form.is_valid(), form.errors
    response = _client(account).post(
        reverse(
            "character-borrow-create",
            kwargs={"character_id": borrower.id, "membership_id": membership.id},
        ),
        payload,
    )
    assert response.status_code == 303
    entry = BorrowedAbilityLog.objects.get()
    assert entry.membership == membership and entry.borrowed_from == source
    page = _client(account).get(
        reverse("character-section", kwargs={"character_id": borrower.id, "section": "bio-arcane"})
    )
    for text in ("Synthetic Resonance", "Shared Sense", "Temporary exhaustion", "Synthetic Family"):
        assert text.encode() in page.content


def test_character_header_exposes_reviewed_ai_paths_and_family_distinction():
    account, workspace = _owner("header@example.invalid")
    character = Character.objects.create(workspace=workspace, name="Synthetic Header")
    page = _client(account).get(
        reverse("character-section", kwargs={"character_id": character.id, "section": "overview"})
    )
    assert (
        reverse("character-fill-description", kwargs={"character_id": character.id}).encode()
        in page.content
    )
    assert (
        reverse("character-ai-assist", kwargs={"character_id": character.id}).encode()
        in page.content
    )
    assert b"Family" in page.content and b"Other Groups" in page.content


def test_fill_review_applies_only_selected_fields_with_provenance():
    account, workspace = _owner("fill-review@example.invalid")
    character = Character.objects.create(
        workspace=workspace, name="Existing Name", personality="Existing personality"
    )
    request_record = AICreativeRequest.objects.create(
        workspace=workspace,
        requested_by=account,
        task_key="character_fill_description",
        instruction="Synthetic description",
        state="ready",
        provider="local_fake",
        model_identifier="deterministic-v1",
        assembled_context="Synthetic",
        context_hash="a" * 64,
    )
    suggestion = AICreativeSuggestion.objects.create(
        workspace=workspace,
        request=request_record,
        original_output="## Name\nProposed Name\n## Personality\nProposed personality",
        reviewed_output="## Name\nProposed Name\n## Personality\nProposed personality",
        structured_output={"Name": "Proposed Name", "Personality": "Proposed personality"},
    )
    proposal = CharacterAIFieldProposal.objects.create(
        workspace=workspace,
        character=character,
        suggestion=suggestion,
        description="Synthetic description",
        proposed_values={"name": "Proposed Name", "personality": "Proposed personality"},
    )
    client = _client(account)
    review_url = reverse(
        "character-fill-review",
        kwargs={"character_id": character.id, "proposal_id": proposal.id},
    )
    page = client.get(review_url)
    assert page.status_code == 200
    assert b"Existing value" in page.content
    applied = client.post(review_url, {"apply_personality": "on"})
    assert applied.status_code == 303
    character.refresh_from_db()
    proposal.refresh_from_db()
    assert character.name == "Existing Name"
    assert character.personality == "Proposed personality"
    assert proposal.applied_fields == ["personality"]
