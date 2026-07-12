import uuid
from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q

from accounts.models import Account
from scenes.models import Scene, SceneSearchProjection
from workspaces.services import get_authorized_workspace

MAX_SEARCH_QUERY_CHARACTERS = 200
MAX_SEARCH_RESULTS = 50
MAX_SNIPPET_CHARACTERS = 240


@dataclass(frozen=True, slots=True)
class SearchResult:
    scene: Scene
    rank: float
    snippet: str


def search_scenes(
    *,
    actor: Account | AnonymousUser,
    workspace_id: uuid.UUID,
    query_text: str,
    include_archived: bool = False,
    limit: int = 20,
) -> list[SearchResult]:
    workspace = get_authorized_workspace(actor, workspace_id)
    query_text = query_text.strip()
    if not query_text:
        return []
    if len(query_text) > MAX_SEARCH_QUERY_CHARACTERS:
        raise ValueError("Search query is too long.")
    if limit < 1 or limit > MAX_SEARCH_RESULTS:
        raise ValueError("Search result limit is invalid.")
    lifecycle = [Scene.Lifecycle.ACTIVE]
    if include_archived:
        lifecycle.append(Scene.Lifecycle.ARCHIVED)
    query = SearchQuery(query_text, config="simple", search_type="plain")
    projections = (
        SceneSearchProjection.objects.select_related("scene", "source_revision")
        .filter(
            workspace=workspace,
            scene__workspace=workspace,
            scene__lifecycle__in=lifecycle,
            source_revision_id=F("scene__current_revision_id"),
            source_scene_version=F("scene__version"),
            projection_schema_version="scene-search-v1",
            search_configuration_version="simple-v1",
        )
        .filter(Q(title_vector=query) | Q(body_vector=query))
        .annotate(
            search_rank=SearchRank(F("title_vector"), query) + SearchRank(F("body_vector"), query)
        )
        .order_by("-search_rank", "scene__ordering", "scene_id")[:limit]
    )
    return [
        SearchResult(
            scene=projection.scene,
            rank=float(projection.search_rank),
            snippet=_plain_excerpt(projection.source_revision.content, query_text),
        )
        for projection in projections
    ]


def _plain_excerpt(content: str, query_text: str) -> str:
    if not content:
        return ""
    token = next((part for part in query_text.casefold().split() if part), "")
    position = content.casefold().find(token) if token else 0
    if position < 0:
        position = 0
    start = max(0, position - MAX_SNIPPET_CHARACTERS // 3)
    end = min(len(content), start + MAX_SNIPPET_CHARACTERS)
    excerpt = content[start:end]
    if start:
        excerpt = "…" + excerpt
    if end < len(content):
        excerpt += "…"
    return excerpt
