from dataclasses import dataclass

from django.db.models import Q

from publishing.models import ExportRecord, ManuscriptProject, PublicationEntry
from workspaces.services import get_authorized_workspace


@dataclass(frozen=True, slots=True)
class PublishingSearchResult:
    record: object
    snippet: str


def search_publishing(*, actor, workspace_id, query_text, limit=20):
    workspace = get_authorized_workspace(actor, workspace_id)
    value = query_text.strip()
    if not value:
        return {"manuscript_results": [], "publication_results": [], "export_results": []}
    manuscripts = ManuscriptProject.objects.filter(workspace=workspace).filter(
        Q(name__icontains=value)
        | Q(title_override__icontains=value)
        | Q(edition_label__icontains=value)
        | Q(description__icontains=value)
    )[:limit]
    publications = PublicationEntry.objects.filter(workspace=workspace).filter(
        Q(public_title__icontains=value)
        | Q(platform_label__icontains=value)
        | Q(notes__icontains=value)
    )[:limit]
    exports = ExportRecord.objects.filter(workspace=workspace).filter(
        Q(filename__icontains=value) | Q(export_format__icontains=value)
    )[:limit]
    return {
        "manuscript_results": [
            PublishingSearchResult(item, item.description[:240]) for item in manuscripts
        ],
        "publication_results": [
            PublishingSearchResult(item, item.notes[:240]) for item in publications
        ],
        "export_results": [
            PublishingSearchResult(
                item, f"{item.get_export_format_display()} · {item.get_status_display()}"
            )
            for item in exports
        ],
    }
