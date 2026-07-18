import os

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character
from decks.draw_services import duplicate_draw, operate, populate_draw, refresh_context_snapshot
from decks.models import (
    Deck,
    DeckCard,
    DeckCategory,
    DrawCardHistory,
    DrawCharacterContext,
    DrawDeckSelection,
    DrawInterpretation,
    FavoriteCard,
    SavedDraw,
    SpreadPosition,
    SpreadTemplate,
)
from stories.models import Chapter, Work
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_world(email="draw@example.invalid"):
    account = Account.objects.create_user(email, password="Synthetic-Draw-Only!")
    workspace = Workspace.objects.create(name="Synthetic Draw Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    work = Work.objects.create(workspace=workspace, title="Synthetic Work", work_type="novel")
    chapter = Chapter.objects.create(
        workspace=workspace,
        work=work,
        title="Synthetic Chapter",
        order=1,
        goal="Reach the threshold",
    )
    deck = Deck.objects.create(
        workspace=workspace, name="Synthetic Deck", source_identity="synthetic-deck"
    )
    category = DeckCategory.objects.create(deck=deck, name="Figure", source_identity="figure")
    cards = [
        DeckCard.objects.create(
            deck=deck,
            category=category,
            stable_source_identity=f"card-{i}",
            title=f"Synthetic Card {i}",
            prompt=f"Synthetic prompt {i}",
            import_checksum=str(i),
            review_status="approved",
            is_active=True,
        )
        for i in range(1, 6)
    ]
    spread = SpreadTemplate.objects.create(
        deck=deck,
        stable_source_identity="spread",
        title="Synthetic Spread",
        instructions="Place in order",
        minimum_cards=2,
        maximum_cards=3,
        allows_redraw=True,
        review_status="approved",
    )
    SpreadPosition.objects.create(
        spread=spread, order=1, name="First", meaning="Opening", required_category=category
    )
    SpreadPosition.objects.create(
        spread=spread, order=2, name="Second", meaning="Change", required_category=category
    )
    SpreadPosition.objects.create(
        spread=spread, order=3, name="Optional", meaning="Echo", is_optional=True
    )
    return workspace, client, work, chapter, deck, category, cards, spread


def make_draw(workspace, deck, **kwargs):
    draw = SavedDraw.objects.create(
        workspace=workspace,
        title="Synthetic Draw",
        primary_deck=deck,
        draw_mode="free_draw",
        random_seed="repeatable-seed",
        **kwargs,
    )
    DrawDeckSelection.objects.create(draw=draw, deck=deck)
    return draw


def test_authenticated_draw_creation_accepts_coherent_story_context():
    workspace, client, work, chapter, deck, _, _, _ = setup_world()
    character = Character.objects.create(
        workspace=workspace, name="Synthetic Context Character", summary="Synthetic summary"
    )

    response = client.post(
        reverse("deck-draw-create"),
        {
            "title": "Synthetic Context Draw",
            "draw_mode": "free_draw",
            "decks": [deck.id],
            "card_count": 2,
            "favorite_mode": "all",
            "work": work.id,
            "chapter": chapter.id,
            "characters": [character.id],
            "author_brief": "Synthetic context validation.",
        },
    )

    assert response.status_code == 302
    draw = SavedDraw.objects.get(title="Synthetic Context Draw")
    assert draw.workspace == workspace and draw.work == work and draw.chapter == chapter
    assert draw.draw_cards.count() == 2
    assert draw.context_snapshot["chapter"]["id"] == str(chapter.id)
    assert draw.context_snapshot["context"][0]["id"] == str(character.id)


def test_seeded_free_and_official_draws_are_deterministic_and_enforce_spread():
    workspace, _, _, _, deck, _, _, spread = setup_world()
    first = make_draw(workspace, deck)
    populate_draw(first, 3)
    second = make_draw(workspace, deck)
    populate_draw(second, 3)
    assert list(first.draw_cards.values_list("card_id", flat=True)) == list(
        second.draw_cards.values_list("card_id", flat=True)
    )
    official = make_draw(workspace, deck, spread=spread)
    official.draw_mode = "official_spread"
    official.save()
    populate_draw(official, 2)
    assert official.draw_cards.count() == 2 and all(
        item.card.category_id for item in official.draw_cards.all()
    )


def test_eligibility_pending_inactive_favorites_and_duplicate_prevention():
    workspace, _, _, _, deck, _, cards, _ = setup_world()
    cards[0].review_status = "pending"
    cards[0].save()
    cards[1].is_active = False
    cards[1].save()
    FavoriteCard.objects.create(workspace=workspace, card=cards[2])
    draw = make_draw(workspace, deck, favorite_mode="only")
    populate_draw(draw, 1)
    assert draw.draw_cards.get().card == cards[2]
    draw.include_pending = True
    draw.include_inactive = True
    draw.favorite_mode = "all"
    draw.save()
    populate_draw(draw, 2)
    assert draw.draw_cards.values("card_id").distinct().count() == 3


def test_context_snapshot_coherence_uniqueness_and_refresh():
    workspace, _, work, chapter, deck, _, _, _ = setup_world()
    draw = make_draw(workspace, deck, work=work, chapter=chapter)
    character = Character.objects.create(
        workspace=workspace, name="Synthetic Hero", summary="Original summary"
    )
    DrawCharacterContext.objects.create(draw=draw, character=character)
    refresh_context_snapshot(draw)
    draw.refresh_from_db()
    assert draw.context_snapshot["chapter"]["goal"] == "Reach the threshold"
    character.summary = "Changed later"
    character.save()
    draw.refresh_from_db()
    assert draw.context_snapshot["context"][0]["summary"] == "Original summary"
    refresh_context_snapshot(draw)
    draw.refresh_from_db()
    assert draw.context_snapshot["context"][0]["summary"] == "Changed later"
    with pytest.raises(IntegrityError):
        DrawCharacterContext.objects.create(draw=draw, character=character)


def test_operations_history_locked_preservation_discard_restore_and_reorder():
    workspace, client, _, _, deck, _, cards, _ = setup_world()
    draw = make_draw(workspace, deck)
    populate_draw(draw, 2)
    item = draw.draw_cards.first()
    operate(item, "lock")
    with pytest.raises(ValidationError):
        operate(item, "redraw")
    operate(item, "unlock")
    operate(item, "replace", replacement=cards[-1])
    operate(item, "discard")
    operate(item, "restore")
    assert DrawCardHistory.objects.filter(draw=draw).count() == 5
    response = client.post(
        reverse("deck-draw-card-action", args=(item.id,)),
        {
            "action": "update",
            "position_order": 2,
            "orientation": "rotated",
            "custom_position_label": "Conflict",
            "author_note": "Keep this tension",
        },
    )
    assert response.status_code == 302
    item.refresh_from_db()
    assert item.position_order == 2 and item.orientation == "rotated"
    assert client.get(reverse("deck-draw-card-action", args=(item.id,))).status_code == 405


def test_interpretation_conversion_chapter_append_replace_duplicate_archive_and_scope():
    workspace, client, work, chapter, deck, _, _, _ = setup_world()
    draw = make_draw(workspace, deck, work=work, chapter=chapter)
    populate_draw(draw, 1)
    response = client.post(
        reverse("deck-draw-interpretation", args=(draw.id,)),
        {
            "title": "Synthetic reading",
            "interpretation_text": "A new turn",
            "unresolved_questions": "Why?",
            "opportunities": "Change",
            "risks_complications": "Cost",
            "author_notes": "Review",
            "status": "accepted",
        },
    )
    assert response.status_code == 302
    interpretation = DrawInterpretation.objects.get(draw=draw)
    response = client.post(
        reverse("deck-draw-conversion", args=(interpretation.id,)),
        {
            "target_type": "chapter",
            "title": "Update",
            "content": "New beat",
            "chapter": chapter.id,
            "chapter_field": "outline",
            "update_mode": "append",
            "work": work.id,
            "confirm": "1",
        },
    )
    chapter.refresh_from_db()
    assert response.status_code == 302 and chapter.outline == "New beat"
    for target in ("character", "group", "location", "region", "codex", "item", "creature"):
        response = client.post(
            reverse("deck-draw-conversion", args=(interpretation.id,)),
            {
                "target_type": target,
                "title": f"Synthetic {target}",
                "content": f"Reviewed {target} content",
                "chapter": chapter.id,
                "chapter_field": "outline",
                "update_mode": "append",
                "work": work.id,
                "confirm": "1",
            },
        )
        assert response.status_code == 302
    client.post(
        reverse("deck-draw-conversion", args=(interpretation.id,)),
        {
            "target_type": "chapter",
            "title": "Replace outline",
            "content": "Replacement outline",
            "chapter": chapter.id,
            "chapter_field": "outline",
            "update_mode": "replace",
            "work": work.id,
            "confirm": "1",
        },
    )
    chapter.refresh_from_db()
    assert chapter.outline == "Replacement outline"
    response = client.post(
        reverse("deck-draw-conversion", args=(interpretation.id,)),
        {
            "target_type": "work",
            "title": "Work note",
            "content": "Reviewed Work addition",
            "chapter": chapter.id,
            "chapter_field": "notes",
            "update_mode": "append",
            "work": work.id,
            "confirm": "1",
        },
    )
    work.refresh_from_db()
    assert response.status_code == 302 and "Reviewed Work addition" in work.description
    assert interpretation.conversions.count() == 10
    clone = duplicate_draw(draw)
    assert (
        clone.draw_cards.count() == draw.draw_cards.count() and clone.interpretations.count() == 0
    )
    client.post(reverse("deck-draw-action", args=(draw.id,)), {"action": "archive"})
    draw.refresh_from_db()
    assert draw.status == "archived"
    client.post(reverse("deck-draw-action", args=(draw.id,)), {"action": "restore"})
    draw.refresh_from_db()
    assert draw.status == "active"
    other, other_client, *_ = setup_world("other-draw@example.invalid")
    assert other_client.get(reverse("deck-draw-detail", args=(draw.id,))).status_code == 404


def test_draw_pages_search_and_dashboard_signal():
    workspace, client, _, _, deck, _, _, _ = setup_world()
    assert b"No saved Draws" in client.get(reverse("deck-draw-list")).content
    draw = make_draw(workspace, deck, author_brief="Synthetic mystery brief")
    populate_draw(draw, 1)
    assert client.get(reverse("deck-draw-detail", args=(draw.id,))).status_code == 200
    assert b"Synthetic Draw" in client.post(reverse("scene-search"), {"query": "mystery"}).content
    assert b"Synthetic Draw" in client.get(reverse("workspace-home")).content
