from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from continuity.forms import (
    CharacterKnowledgeForm,
    ClueForm,
    EventForm,
    ReaderKnowledgeForm,
    RevealForm,
    SecretForm,
    ThreadOverviewForm,
    ThreadPurposeForm,
    scope_form,
)
from continuity.models import (
    CharacterKnowledgeRecord,
    PlotThread,
    ReaderKnowledgeRecord,
    Secret,
    ThreadClue,
    ThreadProgressEvent,
    ThreadReveal,
)
from continuity.services import validate_continuity_record
from timeline.models import TimelineEvent
from workspaces.services import resolve_owner_workspace


def _workspace(request):
    return resolve_owner_workspace(request.user)


def _threads(workspace):
    return PlotThread.objects.filter(workspace=workspace).select_related("work", "volume", "arc")


@never_cache
@login_required
def continuity_home(request):
    workspace = _workspace(request)
    threads = _threads(workspace)
    return render(
        request,
        "continuity/home.html",
        {
            "workspace": workspace,
            "open_count": threads.exclude(
                status__in=("resolved", "abandoned", "superseded")
            ).count(),
            "critical_count": threads.filter(priority__in=("critical", "high"))
            .exclude(status="resolved")
            .count(),
            "endangered_count": threads.filter(
                Q(status="endangered") | Q(health="endangered")
            ).count(),
            "unlinked_count": threads.annotate(
                c=Count("threadchapterlink") + Count("threadscenelink")
            )
            .filter(c=0)
            .count(),
            "unresolved_secrets": Secret.objects.filter(workspace=workspace)
            .exclude(status__in=("exposed", "disproven", "obsolete"))
            .count(),
            "planned_reveals": ThreadReveal.objects.filter(
                thread__workspace=workspace, status="planned"
            )[:10],
            "recent_clues": ThreadClue.objects.filter(
                thread__workspace=workspace, status="planted"
            ).order_by("-updated_at")[:10],
            "recent_resolved": threads.filter(status="resolved").order_by("-updated_at")[:10],
            "by_work": threads.values("work__title")
            .annotate(total=Count("id"))
            .order_by("work__title"),
            "warnings": {
                "resolved_without_notes": threads.filter(
                    status="resolved", resolution_notes=""
                ).count(),
                "planted_without_location": ThreadClue.objects.filter(
                    thread__workspace=workspace, status="planted", chapter=None, scene=None
                ).count(),
                "revealed_without_location": ThreadReveal.objects.filter(
                    thread__workspace=workspace, status="revealed", chapter=None, scene=None
                ).count(),
                "events_without_story_placement": TimelineEvent.objects.filter(workspace=workspace)
                .annotate(placements=Count("eventchapterlink") + Count("eventscenelink"))
                .filter(placements=0)
                .count(),
                "resolved_without_timeline": threads.filter(
                    status="resolved", timeline_links=None
                ).count(),
                "exposed_secret_without_reveal_event": Secret.objects.filter(
                    workspace=workspace, status="exposed", timeline_links=None
                ).count(),
                "knowledge_without_chronology": CharacterKnowledgeRecord.objects.filter(
                    workspace=workspace, learned_story_time="", timeline_links=None
                ).count(),
            },
        },
    )


@never_cache
@login_required
def thread_list(request):
    workspace = _workspace(request)
    threads = _threads(workspace)
    terminal = ("resolved", "abandoned", "superseded")
    if not request.GET.get("include_closed") and not request.GET.get("status"):
        threads = threads.exclude(status__in=terminal)
    for key in ("work", "thread_type", "status", "priority", "visibility", "health"):
        if value := request.GET.get(key, "").strip():
            threads = threads.filter(**({"work_id": value} if key == "work" else {key: value}))
    if query := request.GET.get("query", "").strip():
        threads = threads.filter(
            Q(title__icontains=query)
            | Q(short_summary__icontains=query)
            | Q(description__icontains=query)
            | Q(intended_payoff__icontains=query)
        )
    if request.GET.get("view") == "endangered":
        threads = threads.filter(Q(status="endangered") | Q(health="endangered"))
    if request.GET.get("view") == "priority":
        threads = threads.filter(priority__in=("critical", "high"))
    if request.GET.get("view") == "unlinked":
        threads = threads.annotate(c=Count("threadchapterlink") + Count("threadscenelink")).filter(
            c=0
        )
    if request.GET.get("view") == "resolved":
        threads = threads.filter(status="resolved")
    if character_id := request.GET.get("character", "").strip():
        threads = threads.filter(threadcharacterlink__character_id=character_id)
    return render(
        request,
        "continuity/thread_list.html",
        {
            "workspace": workspace,
            "threads": threads.annotate(
                chapter_count=Count("threadchapterlink", distinct=True),
                scene_count=Count("threadscenelink", distinct=True),
            ),
            "works": workspace.works.all(),
            "filters": request.GET,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def thread_create(request):
    workspace = _workspace(request)
    initial = {"work": request.GET.get("work", "")}
    form = ThreadOverviewForm(request.POST or None, workspace=workspace, initial=initial)
    if request.method == "POST" and form.is_valid():
        thread = form.save(commit=False)
        thread.workspace = workspace
        thread.full_clean()
        thread.save()
        for kind in ("chapter", "scene", "draw", "interpretation"):
            if record_id := request.GET.get(kind):
                _create_thread_link(thread, kind, record_id, "introduced")
        return redirect("continuity-thread-detail", thread.id)
    return render(request, "continuity/form.html", {"form": form, "heading": "Create Plot Thread"})


@never_cache
@login_required
def thread_detail(request, thread_id):
    workspace = _workspace(request)
    thread = get_object_or_404(_threads(workspace), id=thread_id)
    link_options = {}
    for kind, (app_label, record_name, _, _) in THREAD_LINKS.items():
        model = apps.get_model(app_label, record_name)
        scope = (
            {"draw__workspace": workspace} if kind == "interpretation" else {"workspace": workspace}
        )
        link_options[kind] = model.objects.filter(**scope)[:200]
    return render(
        request,
        "continuity/thread_detail.html",
        {
            "workspace": workspace,
            "thread": thread,
            "overview_form": ThreadOverviewForm(instance=thread, workspace=workspace),
            "purpose_form": ThreadPurposeForm(instance=thread),
            "event_form": scope_form(EventForm(), workspace),
            "clue_form": scope_form(ClueForm(), workspace),
            "reveal_form": scope_form(RevealForm(), workspace),
            "secret_form": scope_form(
                SecretForm(initial={"thread": thread, "work": thread.work}), workspace
            ),
            "reader_form": scope_form(
                ReaderKnowledgeForm(initial={"thread": thread, "work": thread.work}), workspace
            ),
            "character_form": scope_form(
                CharacterKnowledgeForm(initial={"thread": thread, "work": thread.work}), workspace
            ),
            "link_options": link_options,
        },
    )


@login_required
@require_POST
def thread_edit(request, thread_id, section):
    workspace = _workspace(request)
    thread = get_object_or_404(_threads(workspace), id=thread_id)
    form = (
        ThreadOverviewForm(request.POST, instance=thread, workspace=workspace)
        if section == "overview"
        else ThreadPurposeForm(request.POST, instance=thread)
    )
    if form.is_valid():
        form.save()
    return redirect("continuity-thread-detail", thread.id)


@login_required
@require_POST
def thread_transition(request, thread_id):
    workspace = _workspace(request)
    thread = get_object_or_404(_threads(workspace), id=thread_id)
    status = request.POST.get("status", "")
    if status not in dict(PlotThread.STATUSES):
        raise Http404
    if status == "resolved" and not request.POST.get("resolution_notes", "").strip():
        raise Http404("Resolution notes are required.")
    thread.status = status
    if status == "resolved":
        thread.resolution_notes = request.POST["resolution_notes"].strip()
        thread.resolved_story_time = request.POST.get("story_time", "").strip()
        thread.health = "resolved"
    elif thread.health == "resolved":
        thread.health = "healthy"
    thread.save()
    return redirect("continuity-thread-detail", thread.id)


THREAD_LINKS = {
    "chapter": ("stories", "Chapter", "ThreadChapterLink", "chapter"),
    "scene": ("scenes", "Scene", "ThreadSceneLink", "scene"),
    "character": ("characters", "Character", "ThreadCharacterLink", "character"),
    "group": ("characters", "CharacterGroup", "ThreadGroupLink", "group"),
    "location": ("worldbuilding", "Location", "ThreadLocationLink", "location"),
    "region": ("worldbuilding", "Region", "ThreadRegionLink", "region"),
    "codex": ("worldbuilding", "CodexEntry", "ThreadCodexLink", "codex"),
    "item": ("worldbuilding", "WorldItem", "ThreadItemLink", "item"),
    "creature": ("worldbuilding", "Creature", "ThreadCreatureLink", "creature"),
    "draw": ("decks", "SavedDraw", "ThreadDrawLink", "draw"),
    "interpretation": ("decks", "DrawInterpretation", "ThreadInterpretationLink", "interpretation"),
}


def _create_thread_link(thread, kind, record_id, role):
    if kind not in THREAD_LINKS:
        raise Http404
    app_label, record_name, link_name, field = THREAD_LINKS[kind]
    record_model = apps.get_model(app_label, record_name)
    link_model = apps.get_model("continuity", link_name)
    scope = (
        {"draw__workspace": thread.workspace}
        if kind == "interpretation"
        else {"workspace": thread.workspace}
    )
    record = get_object_or_404(record_model, id=record_id, **scope)
    link = link_model(thread=thread, role=role or "other", **{field: record})
    link.full_clean()
    link.save()
    return link


@login_required
@require_POST
def thread_link_create(request, thread_id, kind):
    workspace = _workspace(request)
    thread = get_object_or_404(_threads(workspace), id=thread_id)
    _create_thread_link(thread, kind, request.POST.get("record_id"), request.POST.get("role"))
    return redirect("continuity-thread-detail", thread.id)


@login_required
@require_POST
def child_create(request, thread_id, kind):
    workspace = _workspace(request)
    thread = get_object_or_404(_threads(workspace), id=thread_id)
    mapping = {
        "event": (EventForm, ThreadProgressEvent),
        "clue": (ClueForm, ThreadClue),
        "reveal": (RevealForm, ThreadReveal),
    }
    if kind not in mapping:
        raise Http404
    form_class, _ = mapping[kind]
    form = scope_form(form_class(request.POST), workspace)
    if form.is_valid():
        child = form.save(commit=False)
        child.thread = thread
        for record in (getattr(child, "chapter", None), getattr(child, "scene", None)):
            if record and (
                record.workspace_id != workspace.id
                or (thread.work_id and record.work_id != thread.work_id)
            ):
                raise Http404("Story link is incoherent.")
        child.save()
    return redirect("continuity-thread-detail", thread.id)


@login_required
@require_POST
def knowledge_create(request, kind):
    workspace = _workspace(request)
    mapping = {
        "secret": (SecretForm, Secret),
        "reader": (ReaderKnowledgeForm, ReaderKnowledgeRecord),
        "character": (CharacterKnowledgeForm, CharacterKnowledgeRecord),
    }
    if kind not in mapping:
        raise Http404
    form_class, _ = mapping[kind]
    form = scope_form(form_class(request.POST), workspace)
    if form.is_valid():
        record = form.save(commit=False)
        record.workspace = workspace
        if kind != "secret":
            validate_continuity_record(record)
        record.full_clean()
        record.save()
        if kind == "secret":
            return redirect("continuity-secret-detail", record.id)
        if record.thread_id:
            return redirect("continuity-thread-detail", record.thread_id)
    raise Http404("Continuity record is invalid.")


@never_cache
@login_required
def secret_detail(request, secret_id):
    workspace = _workspace(request)
    secret = get_object_or_404(Secret, id=secret_id, workspace=workspace)
    return render(
        request,
        "continuity/secret_detail.html",
        {
            "workspace": workspace,
            "secret": secret,
            "character_knowledge": CharacterKnowledgeRecord.objects.filter(
                workspace=workspace, secret=secret
            ).select_related("character", "chapter", "scene"),
            "reader_knowledge": ReaderKnowledgeRecord.objects.filter(
                workspace=workspace, secret=secret
            ),
            "character_form": scope_form(
                CharacterKnowledgeForm(initial={"secret": secret, "work": secret.work}), workspace
            ),
            "reader_form": scope_form(
                ReaderKnowledgeForm(initial={"secret": secret, "work": secret.work}), workspace
            ),
        },
    )


@login_required
@require_POST
def secret_transition(request, secret_id):
    workspace = _workspace(request)
    secret = get_object_or_404(Secret, id=secret_id, workspace=workspace)
    status = request.POST.get("status", "")
    if status not in ("hidden", "partially_known", "suspected", "exposed", "disproven", "obsolete"):
        raise Http404
    secret.status = status
    secret.save(update_fields=("status", "updated_at"))
    return redirect("continuity-secret-detail", secret.id)
