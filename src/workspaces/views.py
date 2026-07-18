from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from ai_assistance.models import (
    AIChatSession,
    AIContextPack,
    AICreativeSuggestion,
    BrainstormSession,
)
from characters.models import Character
from continuity.models import PlotThread
from decks.models import DeckCard, SavedDraw
from library.models import ResearchSource
from publishing.models import ManuscriptProject
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
from stories.workshop import writing_statistics
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
        "ai_review_count": 0,
        "recent_brainstorm": None,
        "recent_chat": None,
        "writing_statistics": {"today": 0, "week": 0, "streak": 0, "seven_days": []},
        "library_unreviewed_count": 0,
        "publishing_review_count": 0,
        "show_onboarding": True,
        "onboarding_steps": (),
        "onboarding_complete_count": 0,
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
                "ai_review_count": AICreativeSuggestion.objects.filter(
                    workspace=workspace, state__in=("ready", "editing")
                ).count(),
                "recent_brainstorm": BrainstormSession.objects.filter(workspace=workspace)
                .select_related("latest_suggestion", "work")
                .first(),
                "recent_chat": AIChatSession.objects.filter(
                    workspace=workspace, status="active"
                ).first(),
                "writing_statistics": writing_statistics(workspace),
                "library_unreviewed_count": ResearchSource.objects.filter(
                    workspace=workspace, status__in=("unread", "reviewing")
                ).count(),
                "publishing_review_count": ManuscriptProject.objects.filter(
                    workspace=workspace, status="ready"
                ).count(),
                "show_onboarding": not Work.objects.filter(workspace=workspace).exists()
                or not Scene.objects.filter(workspace=workspace).exists(),
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

        first_work = Work.objects.filter(workspace=workspace).order_by("created_at", "id").first()
        first_chapter = (
            Chapter.objects.filter(workspace=workspace).order_by("created_at", "id").first()
        )
        steps = (
            (
                "Create a Work",
                "Give the story a home for Chapters, context, and publishing.",
                bool(first_work),
                reverse("work-create"),
            ),
            (
                "Add the first Chapter",
                "Define one purposeful unit of the reader's journey.",
                bool(first_chapter),
                reverse("chapter-create", args=(first_work.id,))
                if first_work
                else reverse("work-list"),
            ),
            (
                "Create key Characters",
                "Start with the people whose choices move this Chapter.",
                Character.objects.filter(workspace=workspace).exists(),
                reverse("character-create"),
            ),
            (
                "Add immediate world context",
                "Create only the place or concept needed for the next Scene.",
                Location.objects.filter(workspace=workspace).exists(),
                reverse("world-home"),
            ),
            (
                "Create the first Scene",
                "Scenes are the focused units where prose is written.",
                Scene.objects.filter(workspace=workspace).exists(),
                reverse("chapter-detail", args=(first_chapter.work_id, first_chapter.id))
                if first_chapter
                else reverse("scene-create"),
            ),
            (
                "Write and save prose",
                "Every save creates an immutable Revision you can trace.",
                SceneRevision.objects.filter(workspace=workspace).exists(),
                reverse("scene-list"),
            ),
            (
                "Add a Plot Thread",
                "Track a promise, mystery, question, or expected payoff.",
                PlotThread.objects.filter(workspace=workspace).exists(),
                reverse("continuity-thread-create"),
            ),
            (
                "Try a Deck Draw",
                "Use selected Cards as creative prompts, never automatic canon.",
                SavedDraw.objects.filter(workspace=workspace).exists(),
                reverse("deck-draw-create"),
            ),
            (
                "Build an AI Context Pack",
                "Choose exactly what the assistant may use.",
                AIContextPack.objects.filter(workspace=workspace).exists(),
                reverse("ai-context-pack-create"),
            ),
            (
                "Compile a reading copy",
                "Assemble selected immutable Scene Revisions into a Manuscript.",
                ManuscriptProject.objects.filter(workspace=workspace).exists(),
                reverse("publishing-manuscript-create"),
            ),
        )
        context["onboarding_steps"] = tuple(
            {
                "number": number,
                "title": title,
                "description": description,
                "complete": complete,
                "href": href,
            }
            for number, (title, description, complete, href) in enumerate(steps, 1)
        )
        context["onboarding_complete_count"] = sum(step[2] for step in steps)
        context["show_onboarding"] = request.GET.get("onboarding") == "1" or (
            request.GET.get("onboarding") != "hide" and not all(step[2] for step in steps)
        )

    return render(request, "workspaces/home.html", context)


@never_cache
@login_required
def quick_create(request: HttpRequest) -> HttpResponse:
    workspace = resolve_owner_workspace(request.user)
    recent_work = Work.objects.filter(workspace=workspace).order_by("-updated_at", "id").first()
    return render(
        request,
        "workspaces/quick_create.html",
        {"workspace": workspace, "recent_work": recent_work, "active_nav": "create"},
    )


@never_cache
@login_required
def product_guide(request: HttpRequest) -> HttpResponse:
    workspace = resolve_owner_workspace(request.user)
    return render(
        request, "workspaces/product_guide.html", {"workspace": workspace, "active_nav": "help"}
    )
