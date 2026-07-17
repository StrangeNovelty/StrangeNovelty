import uuid
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.db.models import Model, Q

from accounts.models import Account
from workspaces.services import get_authorized_workspace
from worldbuilding.models import CodexEntry, Creature, Location, Region, WorldItem


@dataclass(frozen=True, slots=True)
class WorldSearchResult:
    record: Model
    snippet: str


SEARCH_MODELS = {
    "location_results": (
        Location,
        (
            "name",
            "aliases",
            "summary",
            "description",
            "history",
            "current_state",
            "atmosphere",
            "notable_features",
            "sensory_notes",
            "hazards",
            "culture",
            "travel_notes",
            "notes",
        ),
    ),
    "region_results": (
        Region,
        (
            "name",
            "summary",
            "description",
            "geography",
            "climate",
            "cultures",
            "government",
            "notable_features",
            "hazards",
            "notes",
        ),
    ),
    "codex_results": (
        CodexEntry,
        (
            "term",
            "aliases",
            "definition",
            "description",
            "implications",
            "related_terms",
            "provenance_note",
            "notes",
        ),
    ),
    "item_results": (
        WorldItem,
        (
            "name",
            "aliases",
            "summary",
            "description",
            "appearance",
            "origin",
            "function",
            "capabilities",
            "limitations",
            "costs_dangers",
            "current_condition",
            "notes",
        ),
    ),
    "creature_results": (
        Creature,
        (
            "name",
            "aliases",
            "classification",
            "summary",
            "appearance",
            "biology",
            "habitat",
            "behavior",
            "diet",
            "abilities",
            "weaknesses",
            "signs",
            "ecology",
            "origin",
            "cultural_significance",
            "encounter_notes",
            "notes",
        ),
    ),
}


def search_world(
    *, actor: Account | AnonymousUser, workspace_id: uuid.UUID, query_text: str, limit: int = 20
) -> dict[str, list[WorldSearchResult]]:
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = query_text.strip()
    if not query_text:
        return {key: [] for key in SEARCH_MODELS}
    results: dict[str, list[WorldSearchResult]] = {}
    for key, (model, fields) in SEARCH_MODELS.items():
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": query_text})
        records = model.objects.filter(workspace=workspace).filter(query)[:limit]
        results[key] = [
            WorldSearchResult(record=record, snippet=_snippet(record, fields, query_text))
            for record in records
        ]
    return results


def _snippet(record: Model, fields: tuple[str, ...], query: str) -> str:
    for field in fields:
        text = str(getattr(record, field, ""))
        if query.casefold() in text.casefold():
            return text[:240]
    return str(record)
