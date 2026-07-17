import uuid
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from accounts.models import Account
from decks.models import DeckCard
from workspaces.services import get_authorized_workspace


@dataclass(frozen=True, slots=True)
class CardSearchResult:
    record: DeckCard
    snippet: str


def search_cards(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    query_text: str,
    include_pending: bool = False,
    limit: int = 20,
) -> list[CardSearchResult]:
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = query_text.strip()
    if not query_text:
        return []
    query = (
        Q(title__icontains=query_text)
        | Q(prompt__icontains=query_text)
        | Q(instructions__icontains=query_text)
        | Q(examples__icontains=query_text)
        | Q(role__icontains=query_text)
        | Q(suit__icontains=query_text)
        | Q(category__name__icontains=query_text)
        | Q(expansion__name__icontains=query_text)
        | Q(deck__name__icontains=query_text)
    )
    cards = DeckCard.objects.filter(deck__workspace=workspace, is_active=True).select_related(
        "deck", "expansion", "category"
    )
    if not include_pending:
        cards = cards.filter(review_status="approved")
    cards = cards.filter(query)[:limit]
    return [
        CardSearchResult(
            card,
            next(
                (
                    str(getattr(card, field))[:240]
                    for field in ("title", "prompt", "instructions", "examples")
                    if query_text.casefold() in str(getattr(card, field)).casefold()
                ),
                card.title,
            ),
        )
        for card in cards
    ]
