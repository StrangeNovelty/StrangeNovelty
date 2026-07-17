from dataclasses import dataclass

from django.db.models import Q

from continuity.models import PlotThread, Secret, ThreadClue, ThreadReveal
from workspaces.services import get_authorized_workspace


@dataclass(frozen=True, slots=True)
class ContinuitySearchResult:
    record: object
    snippet: str


def search_continuity(*, actor, workspace_id, query_text, limit=20):
    workspace = get_authorized_workspace(actor, workspace_id)
    value = query_text.strip()
    if not value:
        return {
            "thread_results": [],
            "secret_results": [],
            "clue_results": [],
            "reveal_results": [],
        }
    threads = PlotThread.objects.filter(workspace=workspace).filter(
        Q(title__icontains=value)
        | Q(short_summary__icontains=value)
        | Q(description__icontains=value)
        | Q(intended_payoff__icontains=value)
        | Q(resolution_notes__icontains=value)
    )[:limit]
    secrets = Secret.objects.filter(workspace=workspace).filter(
        Q(title__icontains=value)
        | Q(truth_statement__icontains=value)
        | Q(public_belief__icontains=value)
        | Q(consequences_if_revealed__icontains=value)
        | Q(notes__icontains=value)
    )[:limit]
    clues = ThreadClue.objects.filter(thread__workspace=workspace).filter(
        Q(title__icontains=value)
        | Q(description__icontains=value)
        | Q(intended_interpretation__icontains=value)
        | Q(reader_interpretation_notes__icontains=value)
    )[:limit]
    reveals = ThreadReveal.objects.filter(thread__workspace=workspace).filter(
        Q(title__icontains=value)
        | Q(description__icontains=value)
        | Q(consequences__icontains=value)
    )[:limit]
    return {
        "thread_results": [
            ContinuitySearchResult(item, item.short_summary[:240]) for item in threads
        ],
        "secret_results": [
            ContinuitySearchResult(item, item.public_belief[:240]) for item in secrets
        ],
        "clue_results": [ContinuitySearchResult(item, item.description[:240]) for item in clues],
        "reveal_results": [
            ContinuitySearchResult(item, item.description[:240]) for item in reveals
        ],
    }
