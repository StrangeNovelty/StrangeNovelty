import uuid
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from accounts.models import Account
from characters.models import Character
from workspaces.services import get_authorized_workspace

SEARCH_FIELDS = (
    "name",
    "aliases",
    "role",
    "summary",
    "personality",
    "goals",
    "internal_conflict",
    "external_conflict",
    "voice_notes",
    "notes",
)


@dataclass(frozen=True, slots=True)
class CharacterSearchResult:
    character: Character
    snippet: str


def search_characters(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    query_text: str,
    limit: int = 20,
) -> list[CharacterSearchResult]:
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = query_text.strip()
    if not query_text:
        return []
    if len(query_text) > 200 or limit < 1 or limit > 50:
        raise ValueError("Character search request is invalid.")
    query = Q()
    for field in SEARCH_FIELDS:
        query |= Q(**{f"{field}__icontains": query_text})
    characters = Character.objects.filter(workspace=workspace).filter(query)[:limit]
    return [
        CharacterSearchResult(
            character=character,
            snippet=_character_excerpt(character, query_text),
        )
        for character in characters
    ]


def _character_excerpt(character: Character, query_text: str) -> str:
    token = query_text.casefold()
    for field in SEARCH_FIELDS:
        value = str(getattr(character, field, ""))
        if token in value.casefold():
            value = value.replace("\n", " ").strip()
            return value[:237] + "…" if len(value) > 240 else value
    return character.summary[:240]
