from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from characters.models import Character
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
from stories.models import Work
from workspaces.services import resolve_owner_workspace


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
            }
        )

    return render(request, "workspaces/home.html", context)
