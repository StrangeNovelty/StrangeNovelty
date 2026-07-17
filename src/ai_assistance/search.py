from dataclasses import dataclass

from django.db.models import Q

from ai_assistance.models import AIChatSession, AIContextPack, AICreativeSuggestion
from workspaces.services import get_authorized_workspace


@dataclass(frozen=True, slots=True)
class AIWorkspaceSearchResult:
    record: object
    snippet: str


def search_ai_workspace(*, actor, workspace_id, query_text, limit=20):
    workspace = get_authorized_workspace(actor, workspace_id)
    value = query_text.strip()
    if not value:
        return {"ai_chat_results": [], "ai_context_pack_results": [], "ai_suggestion_results": []}
    chats = AIChatSession.objects.filter(workspace=workspace).filter(
        Q(title__icontains=value) | Q(pinned_instructions__icontains=value)
    )[:limit]
    packs = AIContextPack.objects.filter(workspace=workspace).filter(
        Q(name__icontains=value)
        | Q(description__icontains=value)
        | Q(author_instructions__icontains=value)
    )[:limit]
    suggestions = AICreativeSuggestion.objects.filter(
        workspace=workspace, state__in=("editing", "accepted", "converted")
    ).filter(Q(reviewed_output__icontains=value) | Q(review_notes__icontains=value))[:limit]
    return {
        "ai_chat_results": [
            AIWorkspaceSearchResult(item, item.pinned_instructions[:240]) for item in chats
        ],
        "ai_context_pack_results": [
            AIWorkspaceSearchResult(item, item.description[:240]) for item in packs
        ],
        "ai_suggestion_results": [
            AIWorkspaceSearchResult(item, item.reviewed_output[:240]) for item in suggestions
        ],
    }
