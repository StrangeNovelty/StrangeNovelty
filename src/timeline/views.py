from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Min
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from timeline.forms import (
    EventChronologyForm,
    EventNarrativeForm,
    EventOverviewForm,
    RelationForm,
    TimelineForm,
)
from timeline.models import Timeline, TimelineEvent
from timeline.services import cross_reference, knowledge_cross_reference, relation_warnings
from workspaces.services import resolve_owner_workspace


def workspace_for(request):
    return resolve_owner_workspace(request.user)


LINK_TYPES = {
    "work": ("stories", "Work", "EventWorkLink", "work", "workspace"),
    "volume": ("stories", "Volume", "EventVolumeLink", "volume", "workspace"),
    "arc": ("stories", "Arc", "EventArcLink", "arc", "workspace"),
    "chapter": ("stories", "Chapter", "EventChapterLink", "chapter", "workspace"),
    "scene": ("scenes", "Scene", "EventSceneLink", "scene", "workspace"),
    "character": ("characters", "Character", "EventCharacterLink", "character", "workspace"),
    "group": ("characters", "CharacterGroup", "EventGroupLink", "group", "workspace"),
    "location": ("worldbuilding", "Location", "EventLocationLink", "location", "workspace"),
    "region": ("worldbuilding", "Region", "EventRegionLink", "region", "workspace"),
    "codex": ("worldbuilding", "CodexEntry", "EventCodexLink", "codex", "workspace"),
    "item": ("worldbuilding", "WorldItem", "EventItemLink", "item", "workspace"),
    "creature": ("worldbuilding", "Creature", "EventCreatureLink", "creature", "workspace"),
    "thread": ("continuity", "PlotThread", "EventThreadLink", "thread", "workspace"),
    "secret": ("continuity", "Secret", "EventSecretLink", "secret", "workspace"),
    "clue": ("continuity", "ThreadClue", "EventClueLink", "clue", "thread__workspace"),
    "reveal": ("continuity", "ThreadReveal", "EventRevealLink", "reveal", "thread__workspace"),
    "reader_knowledge": (
        "continuity",
        "ReaderKnowledgeRecord",
        "EventReaderKnowledgeLink",
        "knowledge",
        "workspace",
    ),
    "character_knowledge": (
        "continuity",
        "CharacterKnowledgeRecord",
        "EventCharacterKnowledgeLink",
        "knowledge",
        "workspace",
    ),
    "draw": ("decks", "SavedDraw", "EventDrawLink", "draw", "workspace"),
    "interpretation": (
        "decks",
        "DrawInterpretation",
        "EventInterpretationLink",
        "interpretation",
        "draw__workspace",
    ),
    "ability": ("characters", "Ability", "EventAbilityLink", "ability", "workspace"),
    "stage": ("characters", "AbilityStage", "EventAbilityStageLink", "stage", "workspace"),
    "ability_event": (
        "characters",
        "AbilityEvent",
        "EventAbilityEventLink",
        "ability_event",
        "workspace",
    ),
    "relationship": (
        "characters",
        "CharacterRelationship",
        "EventRelationshipLink",
        "relationship",
        "workspace",
    ),
}


@never_cache
@login_required
def timeline_home(request):
    workspace = workspace_for(request)
    timelines = Timeline.objects.filter(workspace=workspace).annotate(event_count=Count("events"))
    return render(
        request,
        "timeline/home.html",
        {
            "workspace": workspace,
            "timelines": timelines,
            "active_count": timelines.filter(status="active").count(),
            "unplaced_count": TimelineEvent.objects.filter(workspace=workspace)
            .annotate(placements=Count("eventchapterlink") + Count("eventscenelink"))
            .filter(placements=0)
            .count(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def timeline_create(request):
    workspace = workspace_for(request)
    form = TimelineForm(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.workspace = workspace
        item.full_clean()
        item.save()
        return redirect("timeline-detail", item.id)
    return render(request, "timeline/form.html", {"form": form, "heading": "Create Timeline"})


@never_cache
@login_required
def timeline_detail(request, timeline_id):
    workspace = workspace_for(request)
    timeline = get_object_or_404(Timeline, id=timeline_id, workspace=workspace)
    events = timeline.events.select_related("work")
    view = request.GET.get("view")
    if view == "major":
        events = events.filter(significance="major")
    if view == "historical":
        events = events.filter(event_type="historical_event")
    if view == "uncertain":
        events = events.filter(status__in=("disputed", "speculative"))
    if view == "unplaced":
        events = events.annotate(p=Count("eventchapterlink") + Count("eventscenelink")).filter(p=0)
    return render(
        request,
        "timeline/detail.html",
        {
            "workspace": workspace,
            "timeline": timeline,
            "events": events,
            "form": TimelineForm(instance=timeline, workspace=workspace),
        },
    )


@login_required
@require_POST
def timeline_edit(request, timeline_id):
    workspace = workspace_for(request)
    timeline = get_object_or_404(Timeline, id=timeline_id, workspace=workspace)
    form = TimelineForm(request.POST, instance=timeline, workspace=workspace)
    if form.is_valid():
        form.save()
    return redirect("timeline-detail", timeline.id)


@login_required
@require_POST
def timeline_transition(request, timeline_id):
    workspace = workspace_for(request)
    timeline = get_object_or_404(Timeline, id=timeline_id, workspace=workspace)
    status = request.POST.get("status")
    if status not in dict(Timeline.STATUSES):
        raise Http404
    timeline.status = status
    timeline.save(update_fields=("status", "updated_at"))
    return redirect("timeline-detail", timeline.id)


@login_required
@require_http_methods(["GET", "POST"])
def event_create(request, timeline_id):
    workspace = workspace_for(request)
    timeline = get_object_or_404(Timeline, id=timeline_id, workspace=workspace)
    form = EventOverviewForm(
        request.POST or None,
        workspace=workspace,
        initial={"timeline": timeline, "work": timeline.work},
    )
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.workspace = workspace
        event.full_clean()
        event.save()
        for kind in ("chapter", "scene", "interpretation"):
            if record_id := request.GET.get(kind):
                create_link(
                    event, kind, record_id, "depicts" if kind != "interpretation" else "source"
                )
        return redirect("timeline-event-detail", event.id)
    return render(request, "timeline/form.html", {"form": form, "heading": "Create Timeline Event"})


@never_cache
@login_required
def event_detail(request, event_id):
    workspace = workspace_for(request)
    event = get_object_or_404(
        TimelineEvent.objects.select_related("timeline", "work"), id=event_id, workspace=workspace
    )
    options = {}
    for kind, (app_label, model_name, _, _, scope) in LINK_TYPES.items():
        options[kind] = apps.get_model(app_label, model_name).objects.filter(**{scope: workspace})[
            :200
        ]
    return render(
        request,
        "timeline/event_detail.html",
        {
            "workspace": workspace,
            "event": event,
            "overview_form": EventOverviewForm(instance=event, workspace=workspace),
            "chronology_form": EventChronologyForm(instance=event),
            "narrative_form": EventNarrativeForm(instance=event),
            "relation_form": RelationForm(workspace=workspace, source=event),
            "link_options": options,
            "warnings": relation_warnings(event),
        },
    )


@login_required
@require_POST
def event_edit(request, event_id, section):
    workspace = workspace_for(request)
    event = get_object_or_404(TimelineEvent, id=event_id, workspace=workspace)
    forms = {
        "overview": EventOverviewForm(request.POST, instance=event, workspace=workspace),
        "chronology": EventChronologyForm(request.POST, instance=event),
        "narrative": EventNarrativeForm(request.POST, instance=event),
    }
    if section not in forms:
        raise Http404
    if forms[section].is_valid():
        forms[section].save()
    return redirect("timeline-event-detail", event.id)


@login_required
@require_POST
def event_transition(request, event_id):
    workspace = workspace_for(request)
    event = get_object_or_404(TimelineEvent, id=event_id, workspace=workspace)
    status = request.POST.get("status")
    if status not in dict(TimelineEvent.STATUSES):
        raise Http404
    event.status = status
    event.save(update_fields=("status", "updated_at"))
    return redirect("timeline-event-detail", event.id)


def create_link(event, kind, record_id, role):
    if kind not in LINK_TYPES:
        raise Http404
    app_label, model_name, link_name, field, scope = LINK_TYPES[kind]
    record = get_object_or_404(
        apps.get_model(app_label, model_name), id=record_id, **{scope: event.workspace}
    )
    link = apps.get_model("timeline", link_name)(
        event=event, role=role or "other", **{field: record}
    )
    link.full_clean()
    link.save()


@login_required
@require_POST
def event_link(request, event_id, kind):
    workspace = workspace_for(request)
    event = get_object_or_404(TimelineEvent, id=event_id, workspace=workspace)
    create_link(event, kind, request.POST.get("record_id"), request.POST.get("role"))
    return redirect("timeline-event-detail", event.id)


@login_required
@require_POST
def relation_create(request, event_id):
    workspace = workspace_for(request)
    event = get_object_or_404(TimelineEvent, id=event_id, workspace=workspace)
    form = RelationForm(request.POST, workspace=workspace, source=event)
    if form.is_valid():
        relation = form.save(commit=False)
        relation.source = event
        relation.full_clean()
        relation.save()
    return redirect("timeline-event-detail", event.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def cross_reference_view(request):
    workspace = workspace_for(request)
    results = []
    knowledge = []
    if request.method == "POST":
        if request.POST.get("mode") == "secret_knowledge":
            knowledge = knowledge_cross_reference(workspace, request.POST.get("secret"))
        else:
            results = cross_reference(workspace, request.POST)
    return render(
        request,
        "timeline/cross_reference.html",
        {
            "workspace": workspace,
            "results": results,
            "knowledge_results": knowledge,
            "result_count": len(results) + len(knowledge),
            "searched": request.method == "POST",
            "works": workspace.works.all(),
            "characters": workspace.characters.all(),
            "groups": workspace.character_groups.all(),
            "locations": workspace.locations.all(),
            "items": workspace.world_items.all(),
            "creatures": workspace.creatures.all(),
            "threads": workspace.plot_threads.all(),
            "secrets": workspace.secrets.all(),
        },
    )


@never_cache
@login_required
def reader_order(request, work_id):
    workspace = workspace_for(request)
    work = get_object_or_404(workspace.works, id=work_id)
    events = TimelineEvent.objects.filter(workspace=workspace, work=work).annotate(
        first_reader_order=Min("eventchapterlink__chapter__order"),
        first_scene_order=Min("eventscenelink__scene__structure_order"),
    )
    return render(
        request,
        "timeline/reader_order.html",
        {"workspace": workspace, "work": work, "events": events},
    )
