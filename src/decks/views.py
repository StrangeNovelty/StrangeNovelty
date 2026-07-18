import json
import mimetypes
import re
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import FileResponse, Http404, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from characters.models import Character, CharacterGroup
from decks.draw_services import (
    duplicate_draw,
    eligible_cards,
    operate,
    populate_draw,
    refresh_context_snapshot,
)
from decks.forms import (
    REVIEW_ACTIONS,
    CustomCardForm,
    DeckCardReviewForm,
    DrawConversionForm,
    DrawInterpretationForm,
    DrawSetupForm,
)
from decks.models import (
    Confidence,
    Deck,
    DeckCard,
    DeckCardCue,
    DeckCategory,
    DeckExpansion,
    DeckRule,
    DrawCard,
    DrawCharacterContext,
    DrawCodexContext,
    DrawConversion,
    DrawCreatureContext,
    DrawDeckSelection,
    DrawGroupContext,
    DrawInterpretation,
    DrawItemContext,
    DrawLocationContext,
    DrawRegionContext,
    FavoriteCard,
    JournalTemplate,
    ReviewStatus,
    SavedDraw,
    SpreadTemplate,
)
from stories.models import Work
from workspaces.services import resolve_owner_workspace
from worldbuilding.models import CodexEntry, Creature, Location, Region, WorldItem


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
    return cards.distinct().order_by("stable_source_identity", "id")


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


def _draws(workspace):
    return SavedDraw.objects.filter(workspace=workspace).select_related(
        "work", "chapter", "primary_deck", "spread"
    )


@never_cache
@login_required
def draw_list(request):
    workspace = _workspace(request)
    draws = _draws(workspace)
    for key, field in (
        ("status", "status"),
        ("work", "work_id"),
        ("deck", "primary_deck_id"),
        ("spread", "spread_id"),
    ):
        if value := request.GET.get(key, "").strip():
            draws = draws.filter(**{field: value})
    return render(
        request,
        "decks/draw_list.html",
        {
            "workspace": workspace,
            "draws": draws,
            "works": Work.objects.filter(workspace=workspace),
            "decks": Deck.objects.filter(workspace=workspace),
            "spreads": SpreadTemplate.objects.filter(deck__workspace=workspace),
            "statuses": SavedDraw.Status.choices,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def draw_create(request):
    workspace = _workspace(request)
    form = DrawSetupForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                draw = form.save(commit=False)
                draw.workspace = workspace
                draw.primary_deck = form.cleaned_data["decks"].first()
                draw.random_seed = uuid.uuid4().hex
                draw.full_clean()
                draw.save()
                for order, deck in enumerate(form.cleaned_data["decks"]):
                    DrawDeckSelection.objects.create(draw=draw, deck=deck, order=order)
                draw.selected_expansions.set(form.cleaned_data["expansions"])
                draw.selected_categories.set(form.cleaned_data["categories"])
                specs = (
                    ("characters", DrawCharacterContext, "character"),
                    ("groups", DrawGroupContext, "group"),
                    ("locations", DrawLocationContext, "location"),
                    ("regions", DrawRegionContext, "region"),
                    ("codex_entries", DrawCodexContext, "codex"),
                    ("items", DrawItemContext, "item"),
                    ("creatures", DrawCreatureContext, "creature"),
                )
                for field, model, relation in specs:
                    for order, record in enumerate(form.cleaned_data[field]):
                        link = model(draw=draw, order=order, **{relation: record})
                        link.full_clean()
                        link.save()
                refresh_context_snapshot(draw)
                if draw.draw_mode != SavedDraw.Mode.MANUAL:
                    populate_draw(draw, form.cleaned_data["card_count"])
            return redirect("deck-draw-detail", draw.id)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "decks/draw_form.html", {"workspace": workspace, "form": form})


def _guidance(draw):
    prompts = []
    snapshot = draw.context_snapshot.get("context", [])
    labels = {entry["type"]: entry["name"] for entry in snapshot}
    if "character" in labels:
        prompts.append(f"Which card could {labels['character']} embody, resist, or misunderstand?")
    if "location" in labels or "region" in labels:
        prompts.append("How does the selected place reshape the prompt or its stakes?")
    if "group" in labels:
        prompts.append(f"Could {labels['group']} act as faction, obstacle, patron, or witness?")
    if "item" in labels:
        prompts.append(f"Could {labels['item']} satisfy or complicate an Object cue?")
    if "creature" in labels:
        prompts.append(f"How could {labels['creature']} transform the conflict?")
    if "codex" in labels:
        prompts.append(f"How does {labels['codex']} change the literal reading of a card?")
    if draw.chapter:
        prompts.append("How does this serve the Chapter goal and emotional arc?")
    if draw.adult_audience_guidance or draw.genre_guidance:
        prompts.append("What do the audience and genre boundaries invite or rule out?")
    return prompts


@never_cache
@login_required
def draw_detail(request, draw_id):
    workspace = _workspace(request)
    draw = get_object_or_404(
        _draws(workspace).prefetch_related(
            "decks", "draw_cards__card__cues", "draw_cards__spread_position", "card_history"
        ),
        id=draw_id,
    )
    cards = eligible_cards(draw)
    return render(
        request,
        "decks/draw_detail.html",
        {
            "workspace": workspace,
            "draw": draw,
            "eligible_cards": cards[:500],
            "guidance_prompts": _guidance(draw),
            "rules": DeckRule.objects.filter(deck__in=draw.decks.all())[:20],
            "works": Work.objects.filter(workspace=workspace),
            "chapters": workspace.chapters.all(),
            "characters": Character.objects.filter(workspace=workspace),
            "groups": CharacterGroup.objects.filter(workspace=workspace),
            "locations": Location.objects.filter(workspace=workspace),
            "regions": Region.objects.filter(workspace=workspace),
            "codex_entries": CodexEntry.objects.filter(workspace=workspace),
            "items": WorldItem.objects.filter(workspace=workspace),
            "creatures": Creature.objects.filter(workspace=workspace),
        },
    )


@login_required
@require_POST
def draw_action(request, draw_id):
    workspace = _workspace(request)
    draw = get_object_or_404(_draws(workspace), id=draw_id)
    action = request.POST.get("action", "")
    if action == "archive":
        draw.status = SavedDraw.Status.ARCHIVED
        draw.save(update_fields=("status", "updated_at"))
    elif action == "restore":
        draw.status = SavedDraw.Status.ACTIVE
        draw.save(update_fields=("status", "updated_at"))
    elif action == "refresh_context":
        refresh_context_snapshot(draw)
    elif action == "update_context":
        work_id, chapter_id = request.POST.get("work"), request.POST.get("chapter")
        draw.work = get_object_or_404(Work, id=work_id, workspace=workspace) if work_id else None
        draw.chapter = get_object_or_404(workspace.chapters, id=chapter_id) if chapter_id else None
        if draw.chapter and (not draw.work or draw.chapter.work_id != draw.work_id):
            raise Http404("Chapter must belong to the selected Work.")
        specs = (
            ("characters", DrawCharacterContext, "character", Character),
            ("groups", DrawGroupContext, "group", CharacterGroup),
            ("locations", DrawLocationContext, "location", Location),
            ("regions", DrawRegionContext, "region", Region),
            ("codex_entries", DrawCodexContext, "codex", CodexEntry),
            ("items", DrawItemContext, "item", WorldItem),
            ("creatures", DrawCreatureContext, "creature", Creature),
        )
        with transaction.atomic():
            draw.save(update_fields=("work", "chapter", "updated_at"))
            for field, model, relation, record_model in specs:
                ids = list(dict.fromkeys(request.POST.getlist(field)))
                records = list(record_model.objects.filter(workspace=workspace, id__in=ids))
                if len(records) != len(ids):
                    raise Http404("Context selection is unavailable.")
                model.objects.filter(draw=draw).delete()
                for order, record in enumerate(records):
                    model.objects.create(draw=draw, order=order, **{relation: record})
            refresh_context_snapshot(draw)
    elif action == "duplicate":
        return redirect("deck-draw-detail", duplicate_draw(draw).id)
    elif action == "rename":
        title = request.POST.get("title", "").strip()
        if title:
            draw.title = title
            draw.save(update_fields=("title", "updated_at"))
    elif action == "add_card":
        card = get_object_or_404(_cards(workspace), id=request.POST.get("card_id"))
        if not draw.allow_duplicates and draw.draw_cards.filter(card=card).exists():
            raise Http404("Duplicate Cards are disabled.")
        order = (draw.draw_cards.aggregate(value=Max("position_order"))["value"] or 0) + 1
        item = DrawCard(
            draw=draw,
            card=card,
            position_order=order,
            custom_position_label=request.POST.get("label", "").strip(),
        )
        item.full_clean()
        item.save()
    else:
        raise Http404("Draw action is unavailable.")
    return redirect("deck-draw-detail", draw.id)


@login_required
@require_POST
def draw_card_action(request, draw_card_id):
    workspace = _workspace(request)
    item = get_object_or_404(
        DrawCard.objects.select_related("draw", "card", "spread_position"),
        id=draw_card_id,
        draw__workspace=workspace,
    )
    action = request.POST.get("action", "")
    if action in ("lock", "unlock", "redraw", "discard", "restore"):
        operate(item, action)
    elif action == "replace":
        replacement = get_object_or_404(_cards(workspace), id=request.POST.get("card_id"))
        operate(item, action, replacement=replacement)
    elif action == "update":
        item.author_note = request.POST.get("author_note", "")
        item.custom_position_label = request.POST.get("custom_position_label", "").strip()
        item.orientation = request.POST.get("orientation", "upright")
        requested = int(request.POST.get("position_order", item.position_order))
        if requested != item.position_order:
            other = item.draw.draw_cards.filter(position_order=requested).first()
            old = item.position_order
            if other:
                other.position_order = 1000000
                other.save(update_fields=("position_order",))
            item.position_order = requested
            item.save(
                update_fields=(
                    "position_order",
                    "author_note",
                    "custom_position_label",
                    "orientation",
                )
            )
            if other:
                other.position_order = old
                other.save(update_fields=("position_order",))
        else:
            item.save(update_fields=("author_note", "custom_position_label", "orientation"))
    else:
        raise Http404("Card action is unavailable.")
    return redirect("deck-draw-detail", item.draw_id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def draw_interpretation(request, draw_id):
    workspace = _workspace(request)
    draw = get_object_or_404(_draws(workspace), id=draw_id)
    interpretation = draw.interpretations.order_by("-updated_at").first()
    form = DrawInterpretationForm(request.POST or None, instance=interpretation)
    if request.method == "POST" and form.is_valid():
        interpretation = form.save(commit=False)
        interpretation.draw = draw
        interpretation.provenance = {
            "draw_id": str(draw.id),
            "context_snapshot_at": str(draw.context_snapshot_at or ""),
        }
        interpretation.save()
        draw.status = SavedDraw.Status.INTERPRETED
        draw.save(update_fields=("status", "updated_at"))
        return redirect("deck-draw-interpretation", draw.id)
    return render(
        request,
        "decks/draw_interpretation.html",
        {"workspace": workspace, "draw": draw, "form": form, "interpretation": interpretation},
    )


def _create_conversion_target(workspace, cleaned):
    target, title, content = cleaned["target_type"], cleaned["title"].strip(), cleaned["content"]
    if target == "character":
        return Character.objects.create(workspace=workspace, name=title, summary=content)
    if target == "group":
        return CharacterGroup.objects.create(
            workspace=workspace, name=title, group_type="other", description=content
        )
    if target == "location":
        return Location.objects.create(
            workspace=workspace, name=title, location_type="other", description=content
        )
    if target == "region":
        return Region.objects.create(
            workspace=workspace, name=title, region_type="other", description=content
        )
    if target == "codex":
        return CodexEntry.objects.create(
            workspace=workspace,
            term=title,
            category="other",
            definition=content,
            provenance_note="Created from an author-reviewed Deck Draw interpretation.",
        )
    if target == "item":
        return WorldItem.objects.create(
            workspace=workspace, name=title, item_type="other", description=content
        )
    if target == "creature":
        return Creature.objects.create(
            workspace=workspace, name=title, creature_type="other", encounter_notes=content
        )
    if target == "chapter":
        record = cleaned["chapter"]
        if not record:
            raise ValidationError("Select a Chapter.")
        field = cleaned["chapter_field"]
        current = getattr(record, field)
        setattr(
            record,
            field,
            content
            if cleaned["update_mode"] == "replace"
            else "\n\n".join(part for part in (current, content) if part),
        )
        record.save(update_fields=(field, "updated_at"))
        return record
    record = cleaned["work"]
    if not record:
        raise ValidationError("Select a Work.")
    record.description = "\n\n".join(part for part in (record.description, content) if part)
    record.save(update_fields=("description", "updated_at"))
    return record


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def draw_conversion(request, interpretation_id):
    workspace = _workspace(request)
    interpretation = get_object_or_404(
        DrawInterpretation.objects.select_related("draw"),
        id=interpretation_id,
        draw__workspace=workspace,
    )
    if interpretation.status not in ("accepted", "revised", "converted"):
        raise Http404("Accept or revise the interpretation before conversion.")
    initial = {
        "title": interpretation.title,
        "content": interpretation.interpretation_text,
        "chapter": interpretation.draw.chapter,
        "work": interpretation.draw.work,
    }
    form = DrawConversionForm(request.POST or None, workspace=workspace, initial=initial)
    if request.method == "POST" and form.is_valid() and request.POST.get("confirm") == "1":
        try:
            with transaction.atomic():
                target = _create_conversion_target(workspace, form.cleaned_data)
                conversion = DrawConversion(
                    interpretation=interpretation,
                    target_type=form.cleaned_data["target_type"],
                    action=form.cleaned_data.get("update_mode") or "create",
                    summary=form.cleaned_data["content"][:500],
                )
                setattr(conversion, form.cleaned_data["target_type"], target)
                conversion.save()
                interpretation.status = "converted"
                interpretation.save(update_fields=("status", "updated_at"))
                interpretation.draw.status = SavedDraw.Status.CONVERTED
                interpretation.draw.save(update_fields=("status", "updated_at"))
            return redirect("deck-draw-detail", interpretation.draw_id)
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(
        request,
        "decks/draw_conversion.html",
        {
            "workspace": workspace,
            "interpretation": interpretation,
            "form": form,
            "preview": request.method == "POST",
        },
    )


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
