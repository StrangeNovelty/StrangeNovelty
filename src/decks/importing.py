import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

from decks.models import (
    Confidence,
    Deck,
    DeckCard,
    DeckCardCue,
    DeckCategory,
    DeckExpansion,
    DeckRule,
    ImportBatch,
    ImportSource,
    JournalPrompt,
    JournalSection,
    JournalTemplate,
    ReviewStatus,
    SpreadPosition,
    SpreadTemplate,
)
from workspaces.models import Workspace

SUPPORTED_AUDIT_SCHEMAS = {3}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "record"


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _ids(entries: list[Any]) -> set[str]:
    values = set()
    for entry in entries:
        if isinstance(entry, str):
            values.add(entry)
        elif isinstance(entry, dict):
            identity = entry.get("stable_source_id") or entry.get("id")
            if identity:
                values.add(str(identity))
    return values


@dataclass
class PackageReport:
    accepted: int = 0
    pending: int = 0
    needs_correction: int = 0
    needs_symbol_review: int = 0
    duplicates: int = 0
    conflicts: int = 0
    rejected: int = 0
    malformed: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    decks: int = 0
    expansions: int = 0
    categories: int = 0
    cards: int = 0
    rules: int = 0
    spreads: int = 0
    spread_positions: int = 0
    journals: int = 0
    journal_sections: int = 0
    journal_prompts: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class NormalizedPackage:
    schema_version: int
    source_collection: str
    checksum: str
    cards: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    spreads: list[dict[str, Any]]
    journals: list[dict[str, Any]]
    inventory: list[dict[str, Any]]
    review: dict[str, Any]


def load_and_validate_manifest(path: Path) -> tuple[NormalizedPackage | None, PackageReport]:
    report = PackageReport()
    try:
        raw_bytes = path.read_bytes()
        data = json.loads(raw_bytes)
    except (OSError, json.JSONDecodeError) as exc:
        report.malformed = 1
        report.errors.append(f"Manifest cannot be read as JSON: {exc}")
        return None, report
    if not isinstance(data, dict):
        report.malformed = 1
        report.errors.append("Manifest root must be an object.")
        return None, report
    required = ("schema_version", "cards", "rules", "spreads", "journals")
    missing = [key for key in required if key not in data]
    if missing:
        report.malformed = len(missing)
        report.errors.append(f"Missing required sections: {', '.join(missing)}")
        return None, report
    if data["schema_version"] not in SUPPORTED_AUDIT_SCHEMAS:
        report.malformed = 1
        report.errors.append(f"Unsupported schema version: {data['schema_version']}")
        return None, report
    if not all(isinstance(data[key], list) for key in ("cards", "rules", "spreads", "journals")):
        report.malformed = 1
        report.errors.append("Cards, rules, spreads, and journals must be arrays.")
        return None, report
    seen: set[str] = set()
    valid_cards = []
    for index, card in enumerate(data["cards"]):
        if not isinstance(card, dict):
            report.malformed += 1
            report.errors.append(f"Card {index} must be an object.")
            continue
        identity = str(card.get("stable_source_id", "")).strip()
        if not identity or not str(card.get("deck", "")).strip():
            report.malformed += 1
            report.errors.append(f"Card {index} lacks stable_source_id or deck.")
            continue
        if identity in seen:
            report.duplicates += 1
            report.errors.append(f"Duplicate card stable identity: {identity}")
            continue
        seen.add(identity)
        valid_cards.append(card)
    for sindex, spread in enumerate(data["spreads"]):
        if not isinstance(spread, dict) or not spread.get("name") or not spread.get("deck"):
            report.malformed += 1
            report.errors.append(f"Spread {sindex} lacks name or deck.")
            continue
        positions = spread.get("positions", [])
        orders = [position.get("order") for position in positions if isinstance(position, dict)]
        if len(orders) != len(set(orders)):
            report.conflicts += 1
            report.errors.append(f"Spread {sindex} has duplicate position ordering.")
    if report.errors:
        report.rejected = report.malformed
        return None, report
    package = NormalizedPackage(
        schema_version=data["schema_version"],
        source_collection=str(data.get("source_collection", path.parent.name)),
        checksum=hashlib.sha256(raw_bytes).hexdigest(),
        cards=valid_cards,
        rules=data["rules"],
        spreads=data["spreads"],
        journals=data["journals"],
        inventory=data.get("inventory", []),
        review=data.get("manual_review", {}),
    )
    review = package.review
    missing_ids = _ids(review.get("missing_text", []))
    symbol_ids = _ids(review.get("visual_symbol_review", []))
    for card in valid_cards:
        identity = str(card["stable_source_id"])
        if identity in missing_ids:
            report.needs_correction += 1
        elif identity in symbol_ids:
            report.needs_symbol_review += 1
        else:
            report.pending += 1
    report.accepted = report.cards = len(valid_cards)
    report.rules = len(package.rules)
    report.spreads = len(package.spreads)
    report.spread_positions = sum(len(s.get("positions", [])) for s in package.spreads)
    report.journals = len(package.journals)
    report.journal_sections = sum(len(j.get("sections", [])) for j in package.journals)
    report.journal_prompts = sum(
        len(s.get("prompts", [])) for j in package.journals for s in j.get("sections", [])
    )
    return package, report


def _cues(card: dict[str, Any]) -> list[dict[str, Any]]:
    raw = card.get("cues")
    if not isinstance(raw, list):
        raw = []
        for cue_type, key in (("primary", "primary_cues"), ("secondary", "secondary_cues")):
            for value in card.get(key, []) or []:
                raw.append({"type": cue_type, "text": value})
    output = []
    for order, cue in enumerate(raw, 1):
        if isinstance(cue, str):
            cue = {"text": cue}
        if not isinstance(cue, dict):
            continue
        output.append(
            {
                "cue_type": str(cue.get("type") or cue.get("side") or "cue"),
                "cue_label": str(cue.get("label", "")),
                "cue_text": str(cue.get("text", "")),
                "order": order,
                "symbol": str(cue.get("symbol", "")),
                "orientation": str(cue.get("orientation") or cue.get("side") or ""),
                "source_provenance": {"ocr_alternates": cue.get("ocr_alternates", [])},
            }
        )
    return output


def _card_snapshot(card: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "title",
        "prompt",
        "instructions",
        "examples",
        "back_content",
        "modifiers",
        "symbols",
        "tags",
        "role",
        "suit",
        "mechanical_color",
        "primary_cues",
        "secondary_cues",
        "cues",
    )
    return {
        key: card.get(
            key,
            []
            if key in {"modifiers", "symbols", "tags", "primary_cues", "secondary_cues", "cues"}
            else "",
        )
        for key in keys
    }


def import_package(
    *,
    package: NormalizedPackage,
    workspace: Workspace,
    commit: bool,
    refresh_original_snapshots: bool = False,
) -> PackageReport:
    report = PackageReport()
    missing_ids = _ids(package.review.get("missing_text", []))
    symbol_ids = _ids(package.review.get("visual_symbol_review", []))
    ambiguous_ids = _ids(package.review.get("ambiguous_wording", []))
    deck_names = sorted(
        {
            str(x.get("deck", "")).strip()
            for group in (package.cards, package.rules, package.spreads)
            for x in group
            if x.get("deck")
        }
    )
    report.decks = len(deck_names)
    expansion_keys = sorted(
        {
            (str(x.get("deck", "")), str(x.get("expansion") or "Core"))
            for group in (package.cards, package.rules, package.spreads)
            for x in group
            if x.get("deck")
        }
    )
    category_keys = sorted(
        {
            (
                str(c["deck"]),
                str(c.get("expansion") or "Core"),
                str(c.get("category") or "Uncategorized"),
            )
            for c in package.cards
        }
    )
    report.expansions = len(expansion_keys)
    report.categories = len(category_keys)
    report.cards = report.accepted = len(package.cards)
    report.rules = len(package.rules)
    report.spreads = len(package.spreads)
    report.spread_positions = sum(len(x.get("positions", [])) for x in package.spreads)
    report.journals = len(package.journals)
    report.journal_sections = sum(len(x.get("sections", [])) for x in package.journals)
    report.journal_prompts = sum(
        len(s.get("prompts", [])) for j in package.journals for s in j.get("sections", [])
    )
    for card in package.cards:
        identity = str(card["stable_source_id"])
        if identity in missing_ids:
            report.needs_correction += 1
        elif identity in symbol_ids:
            report.needs_symbol_review += 1
        else:
            report.pending += 1
    if not commit:
        return report
    with transaction.atomic():
        decks = {}
        for name in deck_names:
            deck, created = Deck.objects.get_or_create(
                workspace=workspace,
                source_identity=f"deck:{_slug(name)}",
                defaults={"name": name, "edition": "Imported private collection"},
            )
            decks[name] = deck
            report.created += int(created)
            report.unchanged += int(not created)
        expansions = {}
        for order, (deck_name, name) in enumerate(expansion_keys, 1):
            expansion, created = DeckExpansion.objects.get_or_create(
                deck=decks[deck_name],
                source_identity=f"expansion:{_slug(name)}",
                defaults={"name": name, "order": order},
            )
            expansions[(deck_name, name)] = expansion
            report.created += int(created)
            report.unchanged += int(not created)
        categories = {}
        for order, (deck_name, expansion_name, name) in enumerate(category_keys, 1):
            expansion = expansions[(deck_name, expansion_name)]
            category, created = DeckCategory.objects.get_or_create(
                deck=decks[deck_name],
                source_identity=f"category:{_slug(expansion_name)}:{_slug(name)}",
                defaults={"expansion": expansion, "name": name, "order": order},
            )
            categories[(deck_name, expansion_name, name)] = category
            report.created += int(created)
            report.unchanged += int(not created)
        for raw in package.cards:
            deck_name = str(raw["deck"])
            expansion_name = str(raw.get("expansion") or "Core")
            category_name = str(raw.get("category") or "Uncategorized")
            identity = str(raw["stable_source_id"])
            snapshot = _card_snapshot(raw)
            checksum = _digest(snapshot)
            status = (
                ReviewStatus.NEEDS_CORRECTION
                if identity in missing_ids
                else (
                    ReviewStatus.NEEDS_SYMBOL_REVIEW
                    if identity in symbol_ids
                    else ReviewStatus.PENDING
                )
            )
            defaults = {
                "expansion": expansions[(deck_name, expansion_name)],
                "category": categories[(deck_name, expansion_name, category_name)],
                "card_number": str(raw.get("card_number", "")),
                "title": str(raw.get("title", "")),
                "prompt": str(raw.get("prompt", "")),
                "instructions": str(raw.get("instructions", "")),
                "examples": str(raw.get("examples", "")),
                "back_content": str(raw.get("back_content", "")),
                "suit": str(raw.get("suit", "")),
                "mechanical_color": str(raw.get("mechanical_color", "")),
                "role": str(raw.get("role", "")),
                "modifiers": raw.get("modifiers", []) or [],
                "symbols": raw.get("symbols", []) or [],
                "tags": raw.get("tags", []) or [],
                "source_file_label": str(raw.get("source_file", "")),
                "source_archive_label": str(raw.get("source_archive", "")),
                "source_page": raw.get("source_page") or None,
                "source_position": str(raw.get("source_position", "")),
                "source_checksum": str(raw.get("source_checksum", "")),
                "import_checksum": checksum,
                "extraction_confidence": raw.get("confidence")
                if raw.get("confidence") in Confidence.values
                else Confidence.UNKNOWN,
                "review_status": status,
                "original_extracted_snapshot": snapshot,
                "has_missing_text": identity in missing_ids,
                "has_ambiguous_wording": identity in ambiguous_ids,
                "requires_symbol_review": identity in symbol_ids,
            }
            card, created = DeckCard.objects.get_or_create(
                deck=decks[deck_name], stable_source_identity=identity, defaults=defaults
            )
            if created:
                report.created += 1
                DeckCardCue.objects.bulk_create(
                    [DeckCardCue(card=card, **cue) for cue in _cues(raw)]
                )
            elif card.import_checksum == checksum:
                if refresh_original_snapshots and card.original_extracted_snapshot != snapshot:
                    card.original_extracted_snapshot = snapshot
                    card.save(update_fields=("original_extracted_snapshot", "updated_at"))
                    report.updated += 1
                else:
                    report.unchanged += 1
            else:
                card.import_checksum = checksum
                card.source_file_label = defaults["source_file_label"]
                card.source_archive_label = defaults["source_archive_label"]
                card.source_page = defaults["source_page"]
                card.source_position = defaults["source_position"]
                card.has_missing_text = defaults["has_missing_text"]
                card.has_ambiguous_wording = defaults["has_ambiguous_wording"]
                card.requires_symbol_review = defaults["requires_symbol_review"]
                update_fields = [
                    "import_checksum",
                    "source_file_label",
                    "source_archive_label",
                    "source_page",
                    "source_position",
                    "has_missing_text",
                    "has_ambiguous_wording",
                    "requires_symbol_review",
                    "updated_at",
                ]
                if refresh_original_snapshots:
                    card.original_extracted_snapshot = snapshot
                    update_fields.append("original_extracted_snapshot")
                card.save(update_fields=update_fields)
                report.updated += 1
        for index, raw in enumerate(package.rules, 1):
            deck_name = str(raw["deck"])
            expansion_name = str(raw.get("expansion") or "Core")
            identity_parts = (
                _slug(str(raw.get("source_file", "source"))),
                raw.get("source_page", index),
                _slug(str(raw.get("title", "rule"))),
            )
            identity = f"rule:{identity_parts[0]}:{identity_parts[1]}:{identity_parts[2]}"
            _, created = DeckRule.objects.get_or_create(
                deck=decks[deck_name],
                stable_source_identity=identity,
                defaults={
                    "expansion": expansions[(deck_name, expansion_name)],
                    "title": str(raw.get("title", "Rule")),
                    "rule_type": str(raw.get("rule_type", "")),
                    "rule_text": str(raw.get("text", "")),
                    "order": int(raw.get("order") or index),
                    "source_provenance": {
                        "file": raw.get("source_file", ""),
                        "page": raw.get("source_page"),
                        "section": raw.get("source_section", ""),
                    },
                    "extraction_confidence": raw.get("confidence", Confidence.UNKNOWN),
                },
            )
            report.created += int(created)
            report.unchanged += int(not created)
        for index, raw in enumerate(package.spreads, 1):
            deck_name = str(raw["deck"])
            expansion_name = str(raw.get("expansion") or "Core")
            identity = f"spread:{_slug(expansion_name)}:{_slug(str(raw['name']))}"
            spread, created = SpreadTemplate.objects.get_or_create(
                deck=decks[deck_name],
                stable_source_identity=identity,
                defaults={
                    "expansion": expansions[(deck_name, expansion_name)],
                    "title": str(raw["name"]),
                    "purpose": str(raw.get("purpose", "")),
                    "instructions": str(raw.get("instructions", "")),
                    "minimum_cards": int(raw.get("minimum_cards") or 0),
                    "maximum_cards": int(raw.get("maximum_cards") or 0),
                    "allows_redraw": bool(raw.get("allows_redraw")),
                    "order": index,
                    "source_provenance": {
                        "file": raw.get("source_file", ""),
                        "page": raw.get("source_page") or raw.get("source_section", ""),
                    },
                    "extraction_confidence": raw.get("confidence", Confidence.UNKNOWN),
                },
            )
            report.created += int(created)
            report.unchanged += int(not created)
            if created:
                for pindex, position in enumerate(raw.get("positions", []), 1):
                    label = str(position.get("required_category", ""))
                    category = categories.get((deck_name, expansion_name, label))
                    SpreadPosition.objects.create(
                        spread=spread,
                        order=int(position.get("order") or pindex),
                        name=str(position.get("name", f"Position {pindex}")),
                        meaning=str(position.get("meaning", "")),
                        required_category=category,
                        required_category_label=label,
                        is_optional=bool(position.get("optional")),
                        notes=str(position.get("notes", "")),
                    )
        for raw in package.journals:
            source_identity = f"journal:{_slug(str(raw.get('title', 'journal')))}"
            deck = next(iter(decks.values())) if len(decks) == 1 else decks.get("Deck of Worlds")
            journal, created = JournalTemplate.objects.get_or_create(
                workspace=workspace,
                source_identity=source_identity,
                defaults={
                    "deck": deck,
                    "name": str(raw.get("title", "Journal")),
                    "purpose": str(raw.get("purpose", "")),
                    "instructions": str(raw.get("instructions", "")),
                    "source_provenance": {
                        "file": raw.get("source_file", ""),
                        "section": raw.get("source_page_or_section", ""),
                    },
                },
            )
            report.created += int(created)
            report.unchanged += int(not created)
            if created:
                for sindex, section in enumerate(raw.get("sections", []), 1):
                    model_section = JournalSection.objects.create(
                        journal=journal,
                        title=str(section.get("title", f"Section {sindex}")),
                        guidance=str(section.get("guidance", "")),
                        order=int(section.get("order") or sindex),
                    )
                    for pindex, prompt in enumerate(section.get("prompts", []), 1):
                        JournalPrompt.objects.create(
                            section=model_section,
                            label=str(prompt.get("label", "")),
                            prompt=str(prompt.get("prompt", "")),
                            response_type=str(prompt.get("response_type", "")),
                            order=int(prompt.get("order") or pindex),
                            is_required=bool(prompt.get("required")),
                            notes=str(prompt.get("notes", "")),
                        )
        batch = ImportBatch.objects.create(
            workspace=workspace,
            schema_version=package.schema_version,
            source_package_checksum=package.checksum,
            source_collection_label=Path(package.source_collection).name,
            validation_status="committed",
            created_count=report.created,
            updated_count=report.updated,
            unchanged_count=report.unchanged,
            skipped_count=report.skipped,
            rejected_count=report.rejected,
            conflicted_count=report.conflicts,
            completed_at=timezone.now(),
            report=report.as_dict(),
            provenance={"manifest_checksum": package.checksum},
        )
        ImportSource.objects.bulk_create(
            [
                ImportSource(
                    batch=batch,
                    stable_source_identity=str(item.get("relative_path", index)),
                    path_label=str(item.get("relative_path", "source")),
                    checksum=str(item.get("sha256", "")),
                    source_type=str(item.get("classification", "source")),
                    processing_status="referenced",
                    report={},
                )
                for index, item in enumerate(package.inventory)
                if isinstance(item, dict)
            ]
        )
    return report
