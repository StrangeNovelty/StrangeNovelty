from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from characters.models import Character
from continuity.models import PlotThread
from decks.models import DeckCard, SavedDraw
from scenes.models import Scene, SceneRevision
from security_events.middleware import request_correlation_id
from security_events.services import SecurityEventSpec, record_security_event
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)
from stories.models import Chapter, Work
from timeline.models import TimelineEvent
from workspaces.services import resolve_owner_workspace
from worldbuilding.models import CodexEntry, Creature, Location


@never_cache
def root(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("workspace-home")
    return redirect("login")


@never_cache
@login_required
def workspace_home(request: HttpRequest) -> HttpResponse:
    try:
        workspace = resolve_owner_workspace(request.user)
    except Http404:
        record_security_event(
            SecurityEventSpec(
                event_type=SecurityEventType.WORKSPACE_ACCESS_DENIED,
                outcome=SecurityOutcome.DENIED,
                actor=request.user if request.user.is_authenticated else None,
                target_category=SecurityTargetCategory.WORKSPACE,
                correlation_id=request_correlation_id(request),
                service_role=SecurityServiceRole.WEB,
                reason=SecurityReason.INACCESSIBLE,
            )
        )
        raise
    context: dict[str, object] = {
        "workspace": workspace,
        "active_scene_count": 0,
        "archived_scene_count": 0,
        "revision_count": 0,
        "recent_scenes": (),
        "latest_revision": None,
        "character_count": 0,
        "recent_characters": (),
        "active_work_count": 0,
        "recent_work": None,
        "writing_chapter": None,
        "world_location_count": 0,
        "world_codex_count": 0,
        "world_creature_count": 0,
        "recent_world_record": None,
        "deck_review_remaining": 0,
        "recent_draw": None,
        "continuity_open_count": 0,
        "timeline_unplaced_count": 0,
    }

    # Foundation tests use an unsaved synthetic Workspace. Avoid database
    # queries until the authorized Workspace is a persisted record.
    if not workspace._state.adding:
        workspace_scenes = Scene.objects.filter(workspace=workspace)
        context.update(
            {
                "active_scene_count": workspace_scenes.filter(
                    lifecycle=Scene.Lifecycle.ACTIVE
                ).count(),
                "archived_scene_count": workspace_scenes.filter(
                    lifecycle=Scene.Lifecycle.ARCHIVED
                ).count(),
                "revision_count": SceneRevision.objects.filter(workspace=workspace).count(),
                "recent_scenes": workspace_scenes.filter(lifecycle=Scene.Lifecycle.ACTIVE)
                .select_related("current_revision")
                .order_by("-updated_at", "id")[:4],
                "latest_revision": SceneRevision.objects.filter(workspace=workspace)
                .select_related("scene")
                .order_by("-created_at", "-id")
                .first(),
                "character_count": Character.objects.filter(workspace=workspace).count(),
                "recent_characters": Character.objects.filter(workspace=workspace).order_by(
                    "-updated_at", "id"
                )[:4],
                "active_work_count": Work.objects.filter(
                    workspace=workspace,
                    status__in=(
                        Work.Status.IDEA,
                        Work.Status.PLANNING,
                        Work.Status.DRAFTING,
                        Work.Status.REVISING,
                    ),
                ).count(),
                "recent_work": Work.objects.filter(workspace=workspace)
                .exclude(status=Work.Status.ARCHIVED)
                .order_by("-updated_at", "id")
                .first(),
                "writing_chapter": Chapter.objects.filter(
                    workspace=workspace,
                    status__in=(Chapter.Status.DRAFTING, Chapter.Status.REVISING),
                )
                .select_related("work")
                .order_by("-updated_at", "id")
                .first(),
                "world_location_count": Location.objects.filter(workspace=workspace).count(),
                "world_codex_count": CodexEntry.objects.filter(workspace=workspace).count(),
                "world_creature_count": Creature.objects.filter(workspace=workspace).count(),
                "deck_review_remaining": DeckCard.objects.filter(deck__workspace=workspace)
                .exclude(review_status="approved")
                .count(),
                "recent_draw": SavedDraw.objects.filter(workspace=workspace)
                .exclude(status=SavedDraw.Status.ARCHIVED)
                .order_by("-updated_at")
                .first(),
                "continuity_open_count": PlotThread.objects.filter(workspace=workspace)
                .exclude(status__in=("resolved", "abandoned", "superseded"))
                .count(),
                "timeline_unplaced_count": TimelineEvent.objects.filter(workspace=workspace)
                .annotate(placements=Count("eventchapterlink") + Count("eventscenelink"))
                .filter(placements=0)
                .count(),
            }
        )
        recent_world = []
        for model in (Location, CodexEntry, Creature):
            record = model.objects.filter(workspace=workspace).order_by("-updated_at", "id").first()
            if record:
                recent_world.append(record)
        context["recent_world_record"] = max(
            recent_world, key=lambda item: item.updated_at, default=None
        )

    return render(request, "workspaces/home.html", context)
