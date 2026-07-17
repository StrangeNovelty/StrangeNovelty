import json
import mimetypes
import re
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from decks.forms import REVIEW_ACTIONS, CustomCardForm, DeckCardReviewForm
from decks.models import (
    Confidence,
    Deck,
    DeckCard,
    DeckCardCue,
    DeckCategory,
    DeckExpansion,
    DeckRule,
    FavoriteCard,
    JournalTemplate,
    ReviewStatus,
    SpreadTemplate,
)
from workspaces.services import resolve_owner_workspace


def _workspace(request: HttpRequest):
    return resolve_owner_workspace(request.user)


def _cards(workspace):
    return DeckCard.objects.filter(deck__workspace=workspace).select_related(
        "deck", "expansion", "category"
    )


def _filters(request: HttpRequest) -> dict[str, str]:
    names = (
        "status",
        "confidence",
        "deck",
        "expansion",
        "category",
        "role",
        "missing",
        "ambiguous",
        "symbol",
        "include_unapproved",
        "active",
        "favorite",
        "tag",
        "symbol_label",
        "suit",
        "mechanical_color",
        "query",
    )
    return {
        name: request.GET.get(name, "").strip()
        for name in names
        if request.GET.get(name, "").strip()
    }


def _filtered(workspace, filters, *, review=False):
    cards = _cards(workspace)
    if not review and not filters.get("include_unapproved") and not filters.get("status"):
        cards = cards.filter(review_status=ReviewStatus.APPROVED)
    mapping = {
        "status": "review_status",
        "confidence": "extraction_confidence",
        "deck": "deck_id",
        "expansion": "expansion_id",
        "category": "category_id",
        "role": "role",
        "active": "is_active",
        "suit": "suit",
        "mechanical_color": "mechanical_color",
    }
    for source, target in mapping.items():
        if filters.get(source):
            value = filters[source]
            if source == "active":
                value = value == "true"
            cards = cards.filter(**{target: value})
    if filters.get("missing"):
        cards = cards.filter(has_missing_text=True)
    if filters.get("ambiguous"):
        cards = cards.filter(has_ambiguous_wording=True)
    if filters.get("symbol"):
        cards = cards.filter(requires_symbol_review=True)
    if filters.get("favorite"):
        cards = cards.filter(favorites__workspace=workspace)
    if filters.get("tag"):
        cards = cards.filter(tags__contains=[filters["tag"]])
    if filters.get("symbol_label"):
        cards = cards.filter(symbols__contains=[filters["symbol_label"]])
    if filters.get("query"):
        q = filters["query"]
        cards = cards.filter(
            Q(title__icontains=q)
            | Q(prompt__icontains=q)
            | Q(instructions__icontains=q)
            | Q(role__icontains=q)
            | Q(suit__icontains=q)
        )
    return cards.distinct()


@never_cache
@login_required
def deck_home(request):
    workspace = _workspace(request)
    cards = _cards(workspace)
    context = {
        "workspace": workspace,
        "decks": Deck.objects.filter(workspace=workspace).annotate(card_count=Count("cards")),
        "total_cards": cards.count(),
        "approved": cards.filter(review_status="approved").count(),
        "pending": cards.filter(review_status="pending").count(),
        "needs_correction": cards.filter(review_status="needs_correction").count(),
        "symbol_review": cards.filter(review_status="needs_symbol_review").count(),
        "rule_count": DeckRule.objects.filter(deck__workspace=workspace).count(),
        "spread_count": SpreadTemplate.objects.filter(deck__workspace=workspace).count(),
        "journal_count": JournalTemplate.objects.filter(workspace=workspace).count(),
        "recent_review": cards.exclude(reviewed_at=None).order_by("-reviewed_at").first(),
    }
    return render(request, "decks/home.html", context)


@never_cache
@login_required
def deck_detail(request, deck_id):
    workspace = _workspace(request)
    deck = get_object_or_404(Deck, id=deck_id, workspace=workspace)
    cards = deck.cards.all()
    return render(
        request,
        "decks/deck_detail.html",
        {
            "workspace": workspace,
            "deck": deck,
            "expansions": deck.expansions.annotate(card_count=Count("cards")),
            "categories": deck.categories.annotate(card_count=Count("cards")),
            "card_count": cards.count(),
            "approved": cards.filter(review_status="approved").count(),
        },
    )


@never_cache
@login_required
def card_library(request):
    workspace = _workspace(request)
    filters = _filters(request)
    cards = _filtered(workspace, filters)[:200]
    return render(
        request,
        "decks/card_library.html",
        {
            "workspace": workspace,
            "cards": cards,
            "filters": filters,
            "decks": Deck.objects.filter(workspace=workspace),
            "expansions": DeckExpansion.objects.filter(deck__workspace=workspace),
            "categories": DeckCategory.objects.filter(deck__workspace=workspace),
            "statuses": ReviewStatus.choices,
            "confidences": Confidence.choices,
        },
    )


@never_cache
@login_required
def card_detail(request, card_id):
    workspace = _workspace(request)
    card = get_object_or_404(_cards(workspace).prefetch_related("cues"), id=card_id)
    return render(
        request,
        "decks/card_detail.html",
        {
            "workspace": workspace,
            "card": card,
            "is_favorite": FavoriteCard.objects.filter(workspace=workspace, card=card).exists(),
        },
    )


@never_cache
@login_required
def review_dashboard(request):
    workspace = _workspace(request)
    cards = _cards(workspace)
    filters = _filters(request)
    queue = _filtered(workspace, filters, review=True)
    total = cards.count()
    approved = cards.filter(review_status="approved").count()
    by_deck = Deck.objects.filter(workspace=workspace).annotate(
        card_count=Count("cards"),
        approved_count=Count("cards", filter=Q(cards__review_status="approved")),
    )
    return render(
        request,
        "decks/review_dashboard.html",
        {
            "workspace": workspace,
            "total": total,
            "approved": approved,
            "pending": cards.filter(review_status="pending").count(),
            "needs_correction": cards.filter(review_status="needs_correction").count(),
            "symbol_review": cards.filter(review_status="needs_symbol_review").count(),
            "excluded": cards.filter(review_status="intentionally_excluded").count(),
            "completion": round(approved * 100 / total, 1) if total else 0,
            "remaining": queue.count(),
            "queue_first": queue.first(),
            "filters": filters,
            "by_deck": by_deck,
            "statuses": ReviewStatus.choices,
            "confidences": Confidence.choices,
            "decks": Deck.objects.filter(workspace=workspace),
            "expansions": DeckExpansion.objects.filter(deck__workspace=workspace),
            "categories": DeckCategory.objects.filter(deck__workspace=workspace),
        },
    )


def _queue_context(request, workspace, card):
    filters = _filters(request)
    queue = list(_filtered(workspace, filters, review=True).values_list("id", flat=True))
    position = queue.index(card.id) if card.id in queue else 0
    return (
        filters,
        (queue[position - 1] if position > 0 else None),
        (queue[position + 1] if position + 1 < len(queue) else None),
        position + 1,
        len(queue),
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def review_card(request, card_id):
    workspace = _workspace(request)
    card = get_object_or_404(_cards(workspace).prefetch_related("cues"), id=card_id)
    filters, previous_id, next_id, position, remaining = _queue_context(request, workspace, card)
    form = DeckCardReviewForm(request.POST or None, instance=card)
    if request.method == "POST" and form.is_valid():
        form.save()
        if request.POST.get("save_continue") and next_id:
            return redirect(
                f"{reverse('deck-review-card', args=(next_id,))}?{request.GET.urlencode()}"
            )
        return redirect(f"{reverse('deck-review-card', args=(card.id,))}?{request.GET.urlencode()}")
    return render(
        request,
        "decks/review_card.html",
        {
            "workspace": workspace,
            "card": card,
            "form": form,
            "filters": filters,
            "previous_id": previous_id,
            "next_id": next_id,
            "position": position,
            "remaining": remaining,
            "render_available": _render_path(card) is not None,
        },
    )


@login_required
@require_POST
def review_action(request, card_id):
    workspace = _workspace(request)
    card = get_object_or_404(_cards(workspace), id=card_id)
    action = request.POST.get("action", "")
    continue_after = action.endswith("_continue")
    action = action.removesuffix("_continue")
    if action not in REVIEW_ACTIONS:
        raise Http404("Review action is unavailable.")
    form = DeckCardReviewForm(request.POST, instance=card)
    if form.is_valid():
        card = form.save(commit=False)
        card.review_status = action
        card.reviewed_at = timezone.now()
        card.save()
    query = request.GET.urlencode()
    next_id = request.POST.get("next_id")
    if continue_after and next_id:
        return redirect(f"{reverse('deck-review-card', args=(next_id,))}?{query}")
    return redirect(f"{reverse('deck-review-card', args=(card.id,))}?{query}")


@login_required
@require_POST
def cue_symbol_update(request, cue_id):
    workspace = _workspace(request)
    cue = get_object_or_404(
        DeckCardCue.objects.select_related("card__deck"), id=cue_id, card__deck__workspace=workspace
    )
    label = request.POST.get("semantic_label", "").strip()
    meaning = request.POST.get("meaning", "").strip()
    cue.semantic_label = label
    cue.meaning = meaning
    cue.save(update_fields=("semantic_label", "meaning"))
    if request.POST.get("apply_identical") == "1" and cue.symbol:
        DeckCardCue.objects.filter(card__deck__workspace=workspace, symbol=cue.symbol).update(
            semantic_label=label, meaning=meaning
        )
    return redirect(f"{reverse('deck-review-card', args=(cue.card_id,))}?{request.GET.urlencode()}")


def _render_path(card):
    root_value = getattr(settings, "DECK_AUDIT_ROOT", "")
    if not root_value or not card.source_page:
        return None
    root = Path(root_value)
    try:
        inventory = json.loads((root / "source-inventory.json").read_text())
    except OSError, json.JSONDecodeError:
        return None
    labels = {card.source_file_label, f"{card.source_archive_label}!{card.source_file_label}"}
    record = next(
        (
            item
            for item in inventory
            if item.get("relative_path") in labels
            or item.get("archive_member_path") == card.source_file_label
        ),
        None,
    )
    if not record or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", ""))):
        return None
    render_dir = root / "renders" / record["sha256"]
    for name in (f"page-{card.source_page:02d}.jpg", f"page-{card.source_page}.jpg"):
        candidate = render_dir / name
        if candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()):
            return candidate
    return None


@login_required
@require_GET
def review_render(request, card_id):
    workspace = _workspace(request)
    card = get_object_or_404(_cards(workspace), id=card_id)
    path = _render_path(card)
    if path is None:
        raise Http404("Source render is unavailable.")
    return FileResponse(
        path.open("rb"), content_type=mimetypes.guess_type(path.name)[0] or "image/jpeg"
    )


@login_required
@require_POST
def favorite_toggle(request, card_id):
    workspace = _workspace(request)
    card = get_object_or_404(_cards(workspace), id=card_id)
    favorite, created = FavoriteCard.objects.get_or_create(workspace=workspace, card=card)
    if not created:
        favorite.delete()
    return redirect("deck-card-detail", card.id)


@login_required
@require_POST
def active_toggle(request, card_id):
    workspace = _workspace(request)
    card = get_object_or_404(_cards(workspace), id=card_id)
    card.is_active = not card.is_active
    card.save(update_fields=("is_active", "updated_at"))
    return redirect("deck-card-detail", card.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def custom_card_create(request):
    workspace = _workspace(request)
    form = CustomCardForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        card = form.save(commit=False)
        card.stable_source_identity = f"custom:{uuid.uuid4()}"
        card.import_checksum = "custom"
        card.original_extracted_snapshot = {}
        card.is_custom = True
        card.review_status = ReviewStatus.APPROVED
        card.reviewed_at = timezone.now()
        card.save()
        return redirect("deck-card-detail", card.id)
    return render(request, "decks/custom_card.html", {"workspace": workspace, "form": form})


@never_cache
@login_required
def guidance(request):
    workspace = _workspace(request)
    return render(
        request,
        "decks/guidance.html",
        {
            "workspace": workspace,
            "rules": DeckRule.objects.filter(deck__workspace=workspace).select_related(
                "deck", "expansion"
            ),
            "spreads": SpreadTemplate.objects.filter(deck__workspace=workspace).select_related(
                "deck", "expansion"
            ),
            "journals": JournalTemplate.objects.filter(workspace=workspace),
        },
    )


@never_cache
@login_required
def spread_detail(request, spread_id):
    workspace = _workspace(request)
    spread = get_object_or_404(
        SpreadTemplate.objects.filter(deck__workspace=workspace).prefetch_related("positions"),
        id=spread_id,
    )
    return render(request, "decks/spread_detail.html", {"workspace": workspace, "spread": spread})


@never_cache
@login_required
def journal_detail(request, journal_id):
    workspace = _workspace(request)
    journal = get_object_or_404(
        JournalTemplate.objects.filter(workspace=workspace).prefetch_related("sections__prompts"),
        id=journal_id,
    )
    return render(
        request, "decks/journal_detail.html", {"workspace": workspace, "journal": journal}
    )
