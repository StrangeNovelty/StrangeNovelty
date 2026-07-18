import uuid
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from accounts.models import Account
from stories.models import Chapter, Work
from workspaces.services import get_authorized_workspace

WORK_SEARCH_FIELDS = ("title", "subtitle", "premise", "description", "genre_notes")
CHAPTER_SEARCH_FIELDS = (
    "title",
    "label",
    "summary",
    "concept",
    "goal",
    "key_beats",
    "emotional_arc",
    "character_focus",
    "brain_dump",
    "outline",
    "notes",
)


@dataclass(frozen=True, slots=True)
class WorkSearchResult:
    work: Work
    snippet: str


@dataclass(frozen=True, slots=True)
class ChapterSearchResult:
    chapter: Chapter
    snippet: str


def search_works(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    query_text: str,
    limit: int = 20,
) -> list[WorkSearchResult]:
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = _validate_search(query_text, limit)
    if not query_text:
        return []
    query = _query_for_fields(WORK_SEARCH_FIELDS, query_text)
    works = Work.objects.filter(workspace=workspace).filter(query)[:limit]
    return [
        WorkSearchResult(work=work, snippet=_excerpt(work, WORK_SEARCH_FIELDS, query_text))
        for work in works
    ]


def search_chapters(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    query_text: str,
    limit: int = 20,
) -> list[ChapterSearchResult]:
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = _validate_search(query_text, limit)
    if not query_text:
        return []
    query = _query_for_fields(CHAPTER_SEARCH_FIELDS, query_text)
    query |= Q(structured_beats__title__icontains=query_text)
    query |= Q(structured_beats__summary__icontains=query_text)
    query |= Q(structured_beats__notes__icontains=query_text)
    query |= Q(scenes__briefs__scene_function__icontains=query_text)
    query |= Q(scenes__briefs__author_notes__icontains=query_text)
    query |= Q(checklist_items__label__icontains=query_text)
    chapters = (
        Chapter.objects.filter(workspace=workspace)
        .filter(query)
        .select_related("work")
        .distinct()[:limit]
    )
    return [
        ChapterSearchResult(
            chapter=chapter,
            snippet=_excerpt(chapter, CHAPTER_SEARCH_FIELDS, query_text)
            or "Matched Chapter Workshop planning content.",
        )
        for chapter in chapters
    ]


def _validate_search(query_text: str, limit: int) -> str:
    query_text = query_text.strip()
    if len(query_text) > 200 or limit < 1 or limit > 50:
        raise ValueError("Story structure search request is invalid.")
    return query_text


def _query_for_fields(fields: tuple[str, ...], query_text: str) -> Q:
    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": query_text})
    return query


def _excerpt(record: object, fields: tuple[str, ...], query_text: str) -> str:
    token = query_text.casefold()
    for field in fields:
        value = str(getattr(record, field, ""))
        if token in value.casefold():
            value = value.replace("\n", " ").strip()
            return value[:237] + "…" if len(value) > 240 else value
    return ""
