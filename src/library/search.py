from dataclasses import dataclass

from django.db.models import Q

from library.models import ArtworkAsset, LibraryCollection, ResearchNote, ResearchSource
from workspaces.services import get_authorized_workspace


@dataclass(frozen=True, slots=True)
class LibrarySearchResult:
    record: object
    snippet: str


def search_library(*, actor, workspace_id, query_text, limit=20):
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = query_text.strip()
    if not query_text:
        return {
            "research_source_results": [],
            "research_note_results": [],
            "artwork_results": [],
            "collection_results": [],
        }
    specs = (
        (
            ResearchSource,
            (
                "title",
                "creator",
                "citation",
                "short_summary",
                "relevance",
                "credibility_notes",
                "tags",
                "extracted_text",
            ),
            "research_source_results",
        ),
        (
            ResearchNote,
            (
                "title",
                "summary",
                "note_content",
                "interpretation",
                "story_application",
                "questions",
            ),
            "research_note_results",
        ),
        (
            ArtworkAsset,
            ("title", "description", "creator_source", "alt_text", "visual_notes", "mood"),
            "artwork_results",
        ),
        (LibraryCollection, ("name", "description"), "collection_results"),
    )
    output = {}
    for model, fields, key in specs:
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": query_text})
        records = model.objects.filter(workspace=workspace).filter(query)[:limit]
        output[key] = [
            LibrarySearchResult(record, _snippet(record, fields, query_text)) for record in records
        ]
    return output


def _snippet(record, fields, token):
    for field in fields:
        value = str(getattr(record, field, "")).replace("\n", " ").strip()
        if token.casefold() in value.casefold():
            return value[:237] + ("…" if len(value) > 237 else "")
    return ""
