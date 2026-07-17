import random
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from decks.models import (
    DeckCard,
    DrawCard,
    DrawCardHistory,
    DrawCharacterContext,
    DrawCodexContext,
    DrawCreatureContext,
    DrawDeckSelection,
    DrawGroupContext,
    DrawItemContext,
    DrawLocationContext,
    DrawRegionContext,
    ReviewStatus,
    SavedDraw,
)

CONTEXT_SPECS = (
    (DrawCharacterContext, "character", "name", "summary"),
    (DrawGroupContext, "group", "name", "description"),
    (DrawLocationContext, "location", "name", "summary"),
    (DrawRegionContext, "region", "name", "summary"),
    (DrawCodexContext, "codex", "term", "definition"),
    (DrawItemContext, "item", "name", "summary"),
    (DrawCreatureContext, "creature", "name", "summary"),
)


def refresh_context_snapshot(draw: SavedDraw) -> None:
    snapshot = {"work": None, "chapter": None, "context": []}
    if draw.work:
        snapshot["work"] = {
            "id": str(draw.work_id),
            "title": draw.work.title,
            "premise": draw.work.premise[:500],
        }
    if draw.chapter:
        snapshot["chapter"] = {
            "id": str(draw.chapter_id),
            "title": draw.chapter.title,
            "goal": draw.chapter.goal[:500],
            "emotional_arc": draw.chapter.emotional_arc[:500],
        }
    for model, relation, title_field, summary_field in CONTEXT_SPECS:
        for link in model.objects.filter(draw=draw).select_related(relation):
            record = getattr(link, relation)
            snapshot["context"].append(
                {
                    "type": relation,
                    "id": str(record.id),
                    "name": str(getattr(record, title_field)),
                    "summary": str(getattr(record, summary_field, ""))[:500],
                    "role": link.role,
                    "notes": link.notes[:300],
                }
            )
    draw.context_snapshot = snapshot
    draw.context_snapshot_at = timezone.now()
    draw.save(update_fields=("context_snapshot", "context_snapshot_at", "updated_at"))


def eligible_cards(draw: SavedDraw, *, category_id=None):
    deck_ids = draw.deck_selections.values_list("deck_id", flat=True)
    cards = DeckCard.objects.filter(deck_id__in=deck_ids)
    if draw.selected_expansions.exists():
        cards = cards.filter(expansion__in=draw.selected_expansions.all())
    if draw.selected_categories.exists():
        cards = cards.filter(category__in=draw.selected_categories.all())
    cards = cards.exclude(
        review_status__in=(ReviewStatus.REJECTED_DUPLICATE, ReviewStatus.INTENTIONALLY_EXCLUDED)
    )
    if not draw.include_pending:
        cards = cards.filter(review_status=ReviewStatus.APPROVED)
    if not draw.include_inactive:
        cards = cards.filter(is_active=True)
    if category_id:
        cards = cards.filter(category_id=category_id)
    if draw.favorite_mode == "only":
        cards = cards.filter(favorites__workspace=draw.workspace)
    elif draw.favorite_mode == "exclude":
        cards = cards.exclude(favorites__workspace=draw.workspace)
    if not draw.allow_duplicates:
        cards = cards.exclude(id__in=draw.draw_cards.values("card_id"))
    return cards.distinct()


def seeded_pick(draw: SavedDraw, *, category_id=None, salt=""):
    ids = sorted(
        eligible_cards(draw, category_id=category_id).values_list("id", flat=True), key=str
    )
    if not ids:
        raise ValidationError("No eligible Card satisfies this position.")
    rng = random.Random(f"{draw.random_seed}:{salt}")
    return eligible_cards(draw, category_id=category_id).get(id=rng.choice(ids))


@transaction.atomic
def populate_draw(draw: SavedDraw, count: int) -> None:
    if not draw.random_seed:
        draw.random_seed = uuid.uuid4().hex
        draw.save(update_fields=("random_seed", "updated_at"))
    if draw.spread_id:
        if draw.spread.maximum_cards and count > draw.spread.maximum_cards:
            raise ValidationError("Card count exceeds this Spread's maximum.")
        if draw.spread.minimum_cards and count < draw.spread.minimum_cards:
            raise ValidationError("Card count is below this Spread's minimum.")
        positions = list(draw.spread.positions.all())
        required = [position for position in positions if not position.is_optional]
        positions = (
            required + [p for p in positions if p.is_optional][: max(0, count - len(required))]
        )
        if count < len(required):
            raise ValidationError("Card count cannot omit required Spread positions.")
        for position in positions:
            card = seeded_pick(draw, category_id=position.required_category_id, salt=position.order)
            DrawCard.objects.create(
                draw=draw,
                card=card,
                spread_position=position,
                position_order=position.order,
                custom_position_label=position.name,
            )
    else:
        start = (draw.draw_cards.aggregate(value=Max("position_order"))["value"] or 0) + 1
        for order in range(start, start + count):
            card = seeded_pick(draw, salt=order)
            DrawCard.objects.create(draw=draw, card=card, position_order=order)


def _history(draw_card, action, previous=None, replacement=None, **details):
    sequence = (draw_card.draw.card_history.aggregate(value=Max("sequence"))["value"] or 0) + 1
    return DrawCardHistory.objects.create(
        draw=draw_card.draw,
        draw_card=draw_card,
        previous_card=previous,
        replacement_card=replacement,
        action=action,
        sequence=sequence,
        details=details,
    )


@transaction.atomic
def operate(draw_card: DrawCard, action: str, *, replacement=None) -> None:
    previous = draw_card.card
    if action == "lock":
        draw_card.state = DrawCard.State.LOCKED
    elif action == "unlock":
        draw_card.state = DrawCard.State.ACTIVE
    elif action == "discard":
        draw_card.state = DrawCard.State.DISCARDED
    elif action == "restore":
        draw_card.state = DrawCard.State.ACTIVE
    elif action in ("redraw", "replace"):
        if draw_card.state == DrawCard.State.LOCKED:
            raise ValidationError("Locked Cards cannot be replaced.")
        if replacement is None:
            category = (
                draw_card.spread_position.required_category_id
                if draw_card.spread_position_id
                else None
            )
            replacement = seeded_pick(
                draw_card.draw,
                category_id=category,
                salt=f"{draw_card.position_order}:{draw_card.draw_sequence + 1}",
            )
        if replacement.deck.workspace_id != draw_card.draw.workspace_id:
            raise ValidationError("Replacement must belong to this Workspace.")
        if (
            draw_card.spread_position_id
            and draw_card.spread_position.required_category_id
            and replacement.category_id != draw_card.spread_position.required_category_id
        ):
            raise ValidationError("Replacement does not satisfy the required Category.")
        draw_card.card = replacement
        draw_card.state = DrawCard.State.ACTIVE
        draw_card.draw_sequence += 1
    else:
        raise ValidationError("Unknown Card operation.")
    draw_card.full_clean()
    draw_card.save()
    _history(draw_card, action, previous, replacement)


@transaction.atomic
def duplicate_draw(source: SavedDraw) -> SavedDraw:
    clone = SavedDraw.objects.create(
        workspace=source.workspace,
        title=f"{source.title} (copy)",
        primary_deck=source.primary_deck,
        spread=source.spread,
        draw_mode=source.draw_mode,
        random_seed=source.random_seed,
        work=source.work,
        chapter=source.chapter,
        tone_guidance=source.tone_guidance,
        genre_guidance=source.genre_guidance,
        adult_audience_guidance=source.adult_audience_guidance,
        exclusions=source.exclusions,
        author_brief=source.author_brief,
        context_snapshot=source.context_snapshot,
        context_snapshot_at=source.context_snapshot_at,
        allow_duplicates=source.allow_duplicates,
        include_pending=source.include_pending,
        include_inactive=source.include_inactive,
        favorite_mode=source.favorite_mode,
    )
    for selection in source.deck_selections.all():
        DrawDeckSelection.objects.create(draw=clone, deck=selection.deck, order=selection.order)
    clone.selected_expansions.set(source.selected_expansions.all())
    clone.selected_categories.set(source.selected_categories.all())
    for card in source.draw_cards.all():
        DrawCard.objects.create(
            draw=clone,
            card=card.card,
            spread_position=card.spread_position,
            position_order=card.position_order,
            custom_position_label=card.custom_position_label,
            orientation=card.orientation,
            author_note=card.author_note,
        )
    for model, relation, *_ in CONTEXT_SPECS:
        for link in model.objects.filter(draw=source):
            model.objects.create(
                draw=clone,
                role=link.role,
                notes=link.notes,
                order=link.order,
                **{relation: getattr(link, relation)},
            )
    return clone
