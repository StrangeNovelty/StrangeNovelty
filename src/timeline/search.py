from dataclasses import dataclass

from django.db.models import Q

from timeline.models import Timeline, TimelineEvent
from workspaces.services import get_authorized_workspace


@dataclass(frozen=True, slots=True)
class TimelineSearchResult:
    record: object
    snippet: str


def search_timeline(*, actor, workspace_id, query_text, limit=20):
    workspace = get_authorized_workspace(actor, workspace_id)
    value = query_text.strip()
    if not value:
        return {"timeline_results": [], "timeline_event_results": []}
    timelines = Timeline.objects.filter(workspace=workspace).filter(
        Q(name__icontains=value) | Q(description__icontains=value) | Q(epoch_notes__icontains=value)
    )[:limit]
    events = TimelineEvent.objects.filter(workspace=workspace).filter(
        Q(title__icontains=value)
        | Q(short_summary__icontains=value)
        | Q(description__icontains=value)
        | Q(display_date__icontains=value)
        | Q(uncertainty_notes__icontains=value)
        | Q(consequences__icontains=value)
        | Q(notes__icontains=value)
    )[:limit]
    return {
        "timeline_results": [
            TimelineSearchResult(item, item.description[:240]) for item in timelines
        ],
        "timeline_event_results": [
            TimelineSearchResult(item, item.short_summary[:240]) for item in events
        ],
    }
