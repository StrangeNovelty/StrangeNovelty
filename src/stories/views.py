import uuid
from typing import cast

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from ai_assistance.models import AIContextSceneLink, AICreativeSuggestion
from scenes.exceptions import LifecycleDisallowsMutation
from scenes.models import Scene
from stories.forms import (
    ArcForm,
    ChapterBeatForm,
    ChapterChecklistItemForm,
    ChapterForm,
    ChapterPacingProfileForm,
    ChapterSceneAttachForm,
    ChapterSceneCreateForm,
    ChapterSceneOrderForm,
    SceneBriefForm,
    SnapshotForm,
    VolumeForm,
    WorkForm,
    WorkSearchForm,
)
from stories.models import (
    Arc,
    Chapter,
    ChapterBeat,
    ChapterChecklistItem,
    ChapterPacingProfile,
    ChapterPlanningSnapshot,
    SceneBrief,
    Volume,
    Work,
)
from stories.search import search_works
from stories.services import (
    StoryStructureConflict,
    StoryStructureError,
    StoryStructureInaccessible,
    create_arc,
    create_chapter,
    create_scene_in_chapter,
    create_volume,
    create_work,
    delete_structure_record,
    update_arc,
    update_chapter,
    update_scene_placement,
    update_volume,
    update_work,
)
from stories.workshop import (
    capture_planning_snapshot,
    chapter_progress,
    restore_planning_snapshot,
    writing_statistics,
)
from stories.writing import summarize_chapter
from workspaces.models import Workspace
from workspaces.services import resolve_owner_workspace


def _see_other(location: str) -> HttpResponseRedirect:
    response = HttpResponseRedirect(location)
    response.status_code = 303
    return response


def _workspace(request: HttpRequest) -> Workspace:
    return resolve_owner_workspace(request.user)


def _work(workspace: Workspace, work_id: uuid.UUID) -> Work:
    try:
        return cast(Work, Work.objects.get(id=work_id, workspace=workspace))
    except Work.DoesNotExist as exc:
        raise Http404("Work is unavailable.") from exc


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def work_list(request: HttpRequest) -> HttpResponse:
    workspace = _workspace(request)
    form = WorkSearchForm(request.POST or None)
    searched = request.method == "POST"
    if searched and form.is_valid():
        works = [
            result.work
            for result in search_works(
                actor=request.user,
                workspace_id=workspace.id,
                query_text=form.cleaned_data["query"],
                limit=50,
            )
        ]
        _decorate_work_counts(workspace, works)
    else:
        works = list(
            Work.objects.filter(workspace=workspace)
            .annotate(
                volume_count=Count("volumes", distinct=True),
                arc_count=Count("arcs", distinct=True),
                chapter_count=Count("chapters", distinct=True),
                scene_count=Count("scenes", distinct=True),
            )
            .order_by("-updated_at", "id")
        )
    return render(
        request,
        "stories/work_list.html",
        {"works": works, "form": form, "searched": searched},
        status=422 if searched and not form.is_valid() else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def work_create(request: HttpRequest) -> HttpResponse:
    workspace = _workspace(request)
    form = WorkForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            work = create_work(
                actor=request.user,
                workspace_id=workspace.id,
                values=form.cleaned_data,
            )
        except StoryStructureConflict:
            form.add_error(None, "The Work could not be created.")
        else:
            return _see_other(reverse("work-detail", kwargs={"work_id": work.id}))
    return render(
        request,
        "stories/work_form.html",
        {"form": form, "creating": True},
        status=422 if request.method == "POST" else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def work_detail(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    form = WorkForm(request.POST or None, instance=work)
    if request.method == "POST" and form.is_valid():
        try:
            work = update_work(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Work could not be saved.")
        else:
            return _see_other(reverse("work-detail", kwargs={"work_id": work.id}))
    volumes = work.volumes.order_by("order", "id")
    arcs = work.arcs.select_related("volume").order_by("order", "id")
    chapters = list(
        work.chapters.select_related("volume", "arc", "pov_character").order_by("order", "id")
    )
    chapter_summaries = {chapter.id: summarize_chapter(chapter) for chapter in chapters}
    for chapter in chapters:
        chapter.writing_summary = chapter_summaries[chapter.id]
    work_scenes = Scene.objects.filter(workspace=workspace, work=work).exclude(
        lifecycle=Scene.Lifecycle.TRASHED
    )
    context = {
        "work": work,
        "form": form,
        "volumes": volumes,
        "arcs": arcs,
        "chapters": chapters,
        "scene_count": work_scenes.count(),
        "recent_scenes": work_scenes.select_related("chapter").order_by("-updated_at", "id")[:5],
        "recent_chapters": sorted(chapters, key=lambda item: item.updated_at, reverse=True)[:5],
        "unassigned_scenes": Scene.objects.filter(
            workspace=workspace,
            work__isnull=True,
            lifecycle=Scene.Lifecycle.ACTIVE,
        ).order_by("ordering", "id")[:20],
        "writing_statistics": writing_statistics(workspace, work=work),
    }
    return render(
        request,
        "stories/work_detail.html",
        context,
        status=422 if request.method == "POST" else 200,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def volume_create_view(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    form = VolumeForm(request.POST or None, creating=True)
    if request.method == "POST" and form.is_valid():
        try:
            create_volume(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Volume could not be created. Check its order.")
        else:
            return _see_other(reverse("work-detail", kwargs={"work_id": work.id}))
    return _render_structure_form(
        request,
        work=work,
        form=form,
        heading="Add a Volume",
        support="Use a Volume only when this Work benefits from that level.",
        submit_label="Add Volume",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def volume_edit_view(
    request: HttpRequest, work_id: uuid.UUID, volume_id: uuid.UUID
) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    volume = _volume(workspace, work, volume_id)
    form = VolumeForm(request.POST or None, instance=volume)
    if request.method == "POST" and form.is_valid():
        try:
            update_volume(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                volume_id=volume.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Volume could not be saved. Check its order.")
        else:
            return _see_other(reverse("work-detail", kwargs={"work_id": work.id}))
    return _render_structure_form(
        request,
        work=work,
        form=form,
        heading=f"Edit {volume.title}",
        support="Refine this Volume without changing its contained structure.",
        submit_label="Save Volume",
        record=volume,
        record_kind="volume",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def arc_create_view(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    form = ArcForm(request.POST or None, workspace=workspace, work=work, creating=True)
    if request.method == "POST" and form.is_valid():
        try:
            create_arc(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Arc could not be created. Check its parent and order.")
        else:
            return _see_other(reverse("work-detail", kwargs={"work_id": work.id}))
    return _render_structure_form(
        request,
        work=work,
        form=form,
        heading="Add an Arc",
        support="An Arc may stand directly in the Work or belong to a Volume.",
        submit_label="Add Arc",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def arc_edit_view(request: HttpRequest, work_id: uuid.UUID, arc_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    arc = _arc(workspace, work, arc_id)
    form = ArcForm(request.POST or None, workspace=workspace, work=work, instance=arc)
    if request.method == "POST" and form.is_valid():
        try:
            update_arc(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                arc_id=arc.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Arc could not be saved. Check its parent and order.")
        else:
            return _see_other(reverse("work-detail", kwargs={"work_id": work.id}))
    return _render_structure_form(
        request,
        work=work,
        form=form,
        heading=f"Edit {arc.title}",
        support="Keep this Arc within one coherent Work hierarchy.",
        submit_label="Save Arc",
        record=arc,
        record_kind="arc",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chapter_create_view(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    form = ChapterForm(request.POST or None, workspace=workspace, work=work, creating=True)
    if request.method == "POST" and form.is_valid():
        try:
            chapter = create_chapter(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Chapter could not be created. Check its hierarchy and order.")
        else:
            return _see_other(
                reverse(
                    "chapter-detail",
                    kwargs={"work_id": work.id, "chapter_id": chapter.id},
                )
            )
    return _render_structure_form(
        request,
        work=work,
        form=form,
        heading="Add a Chapter or section",
        support="Use the label field for acts, sequences, interludes, or other author terms.",
        submit_label="Add Chapter",
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chapter_detail(request: HttpRequest, work_id: uuid.UUID, chapter_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    form = ChapterForm(
        request.POST or None,
        workspace=workspace,
        work=work,
        instance=chapter,
    )
    if request.method == "POST" and form.is_valid():
        if chapter.outline and form.cleaned_data.get("outline") != chapter.outline:
            capture_planning_snapshot(
                chapter, label="Before outline replacement", trigger="before_outline_replacement"
            )
        try:
            chapter = update_chapter(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                chapter_id=chapter.id,
                values=form.cleaned_data,
            )
        except StoryStructureError:
            form.add_error(None, "The Chapter could not be saved. Check its hierarchy and order.")
        else:
            return _see_other(
                reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
            )
    writing = summarize_chapter(chapter)
    notices = []
    if chapter.status == Chapter.Status.DRAFTING and not chapter.outline.strip():
        notices.append("This drafting Chapter has no outline.")
    if chapter.status == Chapter.Status.REVISING and not writing.scenes:
        notices.append("This revising Chapter has no Scenes.")
    if chapter.status == Chapter.Status.PUBLISHED and any(
        item.scene.updated_at > chapter.updated_at for item in writing.scenes
    ):
        notices.append("Scene writing changed after this Chapter was marked published.")
    if (
        chapter.status == Chapter.Status.POLISHED
        and chapter.thread_links.filter(thread__priority="critical")
        .exclude(thread__status="resolved")
        .exists()
    ):
        notices.append("This polished Chapter has an unresolved critical Plot Thread.")
    scenes = [
        {
            "summary": scene_summary,
            "active_brief": scene_summary.scene.briefs.filter(status="active").first(),
            "beat_count": scene_summary.scene.chapter_beats.count(),
        }
        for scene_summary in writing.scenes
    ]
    return render(
        request,
        "stories/chapter_detail.html",
        {
            "work": work,
            "chapter": chapter,
            "form": form,
            "writing": writing,
            "workshop_scenes": scenes,
            "beats": chapter.structured_beats.select_related("pov_character", "intended_scene"),
            "pacing": getattr(chapter, "pacing_profile", None),
            "snapshots": chapter.planning_snapshots.all()[:20],
            "checklist": chapter.checklist_items.all(),
            "progress": chapter_progress(chapter),
            "writing_statistics": writing_statistics(workspace, chapter=chapter),
            "planning_notices": notices,
            "draws": workspace.saved_draws.filter(chapter=chapter)[:10],
            "voice_profiles": workspace.voice_profiles.filter(work=work, status="active")[:5],
            "scene_create_form": ChapterSceneCreateForm(prefix="new-scene"),
            "scene_attach_form": ChapterSceneAttachForm(
                workspace=workspace, prefix="existing-scene"
            ),
        },
        status=422 if request.method == "POST" else 200,
    )


def _chapter_redirect(chapter):
    return _see_other(
        reverse("chapter-detail", kwargs={"work_id": chapter.work_id, "chapter_id": chapter.id})
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chapter_beat_create(request, work_id, chapter_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    initial = {
        "order": (
            chapter.structured_beats.order_by("-order").values_list("order", flat=True).first() or 0
        )
        + 1
    }
    form = ChapterBeatForm(request.POST or None, chapter=chapter, initial=initial)
    if request.method == "POST" and form.is_valid():
        beat = form.save(commit=False)
        beat.chapter = chapter
        beat.full_clean()
        beat.save()
        return _chapter_redirect(chapter)
    return render(
        request,
        "stories/workshop_form.html",
        {"form": form, "heading": "Add Chapter Beat", "chapter": chapter},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chapter_beat_edit(request, work_id, chapter_id, beat_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    beat = ChapterBeat.objects.filter(id=beat_id, chapter=chapter).first()
    if not beat:
        raise Http404
    form = ChapterBeatForm(request.POST or None, instance=beat, chapter=chapter)
    if request.method == "POST" and form.is_valid():
        form.save()
        return _chapter_redirect(chapter)
    return render(
        request,
        "stories/workshop_form.html",
        {"form": form, "heading": "Edit Chapter Beat", "chapter": chapter},
    )


@login_required
@require_POST
def chapter_beat_delete(request, work_id, chapter_id, beat_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    ChapterBeat.objects.filter(id=beat_id, chapter=chapter).delete()
    return _chapter_redirect(chapter)


@login_required
@require_POST
def chapter_beat_scene_create(request, work_id, chapter_id, beat_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    beat = ChapterBeat.objects.filter(id=beat_id, chapter=chapter).first()
    if not beat:
        raise Http404
    title = request.POST.get("title", "").strip() or beat.title
    result = create_scene_in_chapter(
        actor=request.user,
        workspace_id=workspace.id,
        work_id=work.id,
        chapter_id=chapter.id,
        title=title,
    )
    beat.intended_scene = result.scene
    beat.status = ChapterBeat.Status.REPRESENTED
    beat.full_clean()
    beat.save(update_fields=("intended_scene", "status", "updated_at"))
    return _see_other(reverse("scene-editor", kwargs={"scene_id": result.scene.id}))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def scene_brief_edit(request, scene_id, brief_id=None):
    workspace = _workspace(request)
    scene = (
        Scene.objects.filter(id=scene_id, workspace=workspace)
        .select_related("current_revision", "chapter", "work")
        .first()
    )
    if not scene or not scene.current_revision:
        raise Http404
    brief = SceneBrief.objects.filter(id=brief_id, scene=scene).first() if brief_id else None
    form = SceneBriefForm(request.POST or None, instance=brief)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            saved = form.save(commit=False)
            saved.scene = scene
            if not saved.source_revision_id:
                saved.source_revision = scene.current_revision
            if saved.status == SceneBrief.Status.ACTIVE:
                SceneBrief.objects.filter(scene=scene, status=SceneBrief.Status.ACTIVE).exclude(
                    id=saved.id
                ).update(status=SceneBrief.Status.SUPERSEDED)
            saved.full_clean()
            saved.save()
        return _see_other(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    return render(
        request,
        "stories/workshop_form.html",
        {"form": form, "heading": "Scene Brief", "scene": scene},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def chapter_pacing(request, work_id, chapter_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    profile, _ = ChapterPacingProfile.objects.get_or_create(chapter=chapter)
    form = ChapterPacingProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        return _chapter_redirect(chapter)
    return render(
        request,
        "stories/workshop_form.html",
        {
            "form": form,
            "heading": "Chapter Pacing Profile",
            "chapter": chapter,
            "score_help": "Scores run from 1 (low) through 10 (high). Blank means not assessed.",
        },
    )


@login_required
@require_POST
def chapter_snapshot_create(request, work_id, chapter_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    form = SnapshotForm(request.POST)
    if not form.is_valid():
        raise Http404
    capture_planning_snapshot(chapter, label=form.cleaned_data["label"])
    return _chapter_redirect(chapter)


@login_required
@require_POST
def chapter_snapshot_restore(request, work_id, chapter_id, snapshot_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    snapshot = ChapterPlanningSnapshot.objects.filter(id=snapshot_id, chapter=chapter).first()
    if not snapshot:
        raise Http404
    restore_planning_snapshot(snapshot)
    return _chapter_redirect(chapter)


@login_required
@require_POST
def chapter_snapshot_delete(request, work_id, chapter_id, snapshot_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    ChapterPlanningSnapshot.objects.filter(id=snapshot_id, chapter=chapter).delete()
    return _chapter_redirect(chapter)


@login_required
@require_POST
def chapter_checklist_create(request, work_id, chapter_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    form = ChapterChecklistItemForm(request.POST)
    if not form.is_valid():
        raise Http404
    item = form.save(commit=False)
    item.chapter = chapter
    item.save()
    return _chapter_redirect(chapter)


@login_required
@require_POST
def chapter_checklist_action(request, work_id, chapter_id, item_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    item = ChapterChecklistItem.objects.filter(id=item_id, chapter=chapter).first()
    if not item:
        raise Http404
    if request.POST.get("action") == "delete":
        item.delete()
    else:
        item.completed = not item.completed
        item.save(update_fields=("completed", "updated_at"))
    return _chapter_redirect(chapter)


@login_required
@require_POST
def chapter_status_transition(request, work_id, chapter_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    status = request.POST.get("status")
    if status not in Chapter.Status.values:
        raise Http404
    chapter.status = status
    chapter.full_clean()
    chapter.save(update_fields=("status", "updated_at"))
    return _chapter_redirect(chapter)


@never_cache
@login_required
def series_map(request, work_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapters = list(
        work.chapters.select_related("volume", "arc", "pov_character", "pacing_profile")
        .prefetch_related("structured_beats")
        .order_by("order")
    )
    status = request.GET.get("status")
    volume = request.GET.get("volume")
    arc = request.GET.get("arc")
    pov = request.GET.get("pov")
    if status:
        chapters = [c for c in chapters if c.status == status]
    if volume:
        chapters = [c for c in chapters if str(c.volume_id) == volume]
    if arc:
        chapters = [c for c in chapters if str(c.arc_id) == arc]
    if pov:
        chapters = [c for c in chapters if str(c.pov_character_id) == pov]
    if request.GET.get("no_scenes"):
        chapters = [c for c in chapters if not c.scenes.exclude(lifecycle="trashed").exists()]
    if request.GET.get("no_outline"):
        chapters = [c for c in chapters if not c.outline.strip()]
    if request.GET.get("critical"):
        chapters = [
            c
            for c in chapters
            if c.thread_links.filter(thread__priority="critical")
            .exclude(thread__status="resolved")
            .exists()
        ]
    for chapter in chapters:
        chapter.writing_summary = summarize_chapter(chapter)
        chapter.thread_count = chapter.thread_links.count()
    return render(
        request,
        "stories/series_map.html",
        {
            "work": work,
            "chapters": chapters,
            "volumes": work.volumes.all(),
            "arcs": work.arcs.all(),
            "statuses": Chapter.Status.choices,
            "pov_characters": workspace.characters.order_by("name"),
        },
    )


@never_cache
@login_required
def pacing_map(request, work_id):
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapters = list(
        work.chapters.select_related("pacing_profile", "pov_character", "volume", "arc").order_by(
            "order"
        )
    )
    volume = request.GET.get("volume")
    arc = request.GET.get("arc")
    if volume:
        chapters = [chapter for chapter in chapters if str(chapter.volume_id) == volume]
    if arc:
        chapters = [chapter for chapter in chapters if str(chapter.arc_id) == arc]
    for chapter in chapters:
        chapter.writing_summary = summarize_chapter(chapter)
    missing = sum(not hasattr(c, "pacing_profile") for c in chapters)
    signals = [f"{missing} Chapter(s) have no pacing profile."] if missing else []
    metrics = (
        ("tension_score", "tension"),
        ("dread_score", "dread"),
        ("emotional_intimacy_score", "emotional intimacy"),
        ("relationship_tension_score", "relationship tension"),
        ("pacing_energy_score", "pacing energy"),
        ("humor_score", "humor"),
    )
    for left, right in zip(chapters, chapters[1:], strict=False):
        if not hasattr(left, "pacing_profile") or not hasattr(right, "pacing_profile"):
            continue
        identical = [
            label
            for field, label in metrics
            if getattr(left.pacing_profile, field) is not None
            and getattr(left.pacing_profile, field) == getattr(right.pacing_profile, field)
        ]
        if identical:
            signals.append(f"{left.title} and {right.title} share {', '.join(identical)} scores.")
    profiled = [
        chapter.pacing_profile for chapter in chapters if hasattr(chapter, "pacing_profile")
    ]
    if len(profiled) >= 4 and all(
        profile.pacing_energy_score is None or profile.pacing_energy_score >= 7
        for profile in profiled
    ):
        signals.append("This selection has a long run with no low-energy Chapter.")
    if len(profiled) >= 4 and all(
        profile.humor_score is None or profile.humor_score <= 1 for profile in profiled
    ):
        signals.append("This selection has a long run with little or no marked humor.")
    for field, label in metrics:
        extreme = sum((getattr(profile, field) or 0) >= 9 for profile in profiled)
        if extreme >= 3:
            signals.append(f"{extreme} Chapters cluster at extreme {label} scores.")
    return render(
        request,
        "stories/pacing_map.html",
        {
            "work": work,
            "chapters": chapters,
            "signals": signals,
            "volumes": work.volumes.all(),
            "arcs": work.arcs.all(),
        },
    )


@login_required
@require_POST
def apply_workshop_suggestion(request, suggestion_id):
    workspace = _workspace(request)
    suggestion = (
        AICreativeSuggestion.objects.select_related("request__context_pack__chapter")
        .filter(id=suggestion_id, workspace=workspace, state__in=("accepted", "editing"))
        .first()
    )
    if not suggestion:
        raise Http404
    if suggestion.request.task_key == "chapter_outline":
        pack = suggestion.request.context_pack
        chapter = pack.chapter if pack else None
        if not chapter or chapter.workspace_id != workspace.id:
            raise Http404("The reviewed suggestion needs a Chapter Context Pack.")
        raw = suggestion.structured_output.get("Key Beats") or suggestion.reviewed_output
        values = raw if isinstance(raw, list) else str(raw).splitlines()
        values = [str(value).strip(" -0123456789.\t") for value in values if str(value).strip()]
        capture_planning_snapshot(
            chapter, label="Before AI Beat creation", trigger="before_ai_application"
        )
        start = (
            chapter.structured_beats.order_by("-order").values_list("order", flat=True).first() or 0
        )
        for offset, value in enumerate(values, 1):
            ChapterBeat.objects.create(
                chapter=chapter, order=start + offset, title=value[:240], summary=value
            )
        return _chapter_redirect(chapter)
    if suggestion.request.task_key == "scene_brief":
        pack = suggestion.request.context_pack
        link = (
            AIContextSceneLink.objects.filter(pack=pack)
            .select_related("scene__current_revision")
            .first()
        )
        if not link or not link.scene.current_revision:
            raise Http404("The reviewed suggestion needs a Scene Context Pack.")
        scene = link.scene
        sections = suggestion.structured_output
        with transaction.atomic():
            SceneBrief.objects.filter(scene=scene, status="active").update(status="superseded")
            SceneBrief.objects.create(
                scene=scene,
                source_revision=scene.current_revision,
                status="active",
                pov=str(sections.get("POV", "")),
                scene_function=str(sections.get("Scene Function", "")),
                character_wants=str(sections.get("Character Wants", "")),
                primary_conflict=str(sections.get("Main Conflict", "")),
                stakes=str(sections.get("Stakes", "")),
                setting=str(sections.get("Setting and Atmosphere", "")),
                blocking_and_beats=str(sections.get("Blocking and Beats", "")),
                emotional_movement=str(sections.get("Emotional Movement", "")),
                continuity_concerns=str(sections.get("Continuity Risks", "")),
                opening_beat=str(sections.get("Opening Beat", "")),
                ending_hook=str(sections.get("Ending Hook", "")),
                author_notes="Created from an explicitly reviewed AI Scene Brief suggestion.",
            )
        return _see_other(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    raise Http404("This suggestion has no Chapter Workshop application.")


@never_cache
@login_required
@require_POST
def chapter_scene_create(
    request: HttpRequest, work_id: uuid.UUID, chapter_id: uuid.UUID
) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    form = ChapterSceneCreateForm(request.POST, prefix="new-scene")
    if not form.is_valid():
        raise Http404("Scene title is invalid.")
    try:
        result = create_scene_in_chapter(
            actor=request.user,
            workspace_id=workspace.id,
            work_id=work.id,
            chapter_id=chapter.id,
            title=form.cleaned_data["title"],
        )
    except StoryStructureError as exc:
        raise Http404("Scene could not be created.") from exc
    return _see_other(reverse("scene-editor", kwargs={"scene_id": result.scene.id}))


@never_cache
@login_required
@require_POST
def chapter_scene_attach(
    request: HttpRequest, work_id: uuid.UUID, chapter_id: uuid.UUID
) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    form = ChapterSceneAttachForm(request.POST, workspace=workspace, prefix="existing-scene")
    if not form.is_valid():
        raise Http404("Scene is unavailable.")
    scene = cast(Scene, form.cleaned_data["scene"])
    try:
        update_scene_placement(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            values={
                "work": work,
                "volume": chapter.volume,
                "arc": chapter.arc,
                "chapter": chapter,
                "structure_order": None,
            },
        )
    except (StoryStructureError, LifecycleDisallowsMutation) as exc:
        raise Http404("Scene is unavailable.") from exc
    return _see_other(
        reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
    )


@never_cache
@login_required
@require_POST
def chapter_scene_order(
    request: HttpRequest,
    work_id: uuid.UUID,
    chapter_id: uuid.UUID,
    scene_id: uuid.UUID,
) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    scene = _chapter_scene(workspace, chapter, scene_id)
    form = ChapterSceneOrderForm(request.POST)
    if not form.is_valid():
        raise Http404("Scene order is invalid.")
    try:
        update_scene_placement(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            values={
                "work": work,
                "volume": chapter.volume,
                "arc": chapter.arc,
                "chapter": chapter,
                "structure_order": form.cleaned_data["structure_order"],
            },
        )
    except (StoryStructureError, LifecycleDisallowsMutation) as exc:
        raise Http404("Scene order could not be updated.") from exc
    return _see_other(
        reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
    )


@never_cache
@login_required
@require_POST
def chapter_scene_detach(
    request: HttpRequest,
    work_id: uuid.UUID,
    chapter_id: uuid.UUID,
    scene_id: uuid.UUID,
) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    chapter = _chapter(workspace, work, chapter_id)
    scene = _chapter_scene(workspace, chapter, scene_id)
    try:
        update_scene_placement(
            actor=request.user,
            workspace_id=workspace.id,
            scene_id=scene.id,
            values={
                "work": work,
                "volume": chapter.volume,
                "arc": chapter.arc,
                "chapter": None,
                "structure_order": None,
            },
        )
    except (StoryStructureError, LifecycleDisallowsMutation) as exc:
        raise Http404("Scene could not be detached.") from exc
    return _see_other(
        reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def structure_delete_view(
    request: HttpRequest,
    work_id: uuid.UUID,
    record_kind: str,
    record_id: uuid.UUID | None = None,
) -> HttpResponse:
    workspace = _workspace(request)
    work = _work(workspace, work_id)
    effective_record_id = work.id if record_id is None else record_id
    record = _structure_record(workspace, work, record_kind, effective_record_id)
    error = ""
    if request.method == "POST":
        try:
            delete_structure_record(
                actor=request.user,
                workspace_id=workspace.id,
                work_id=work.id,
                record_kind=record_kind,
                record_id=record.id,
            )
        except StoryStructureConflict:
            error = "Reassign contained structure and Scenes before deleting this item."
        except StoryStructureInaccessible as exc:
            raise Http404("Structure record is unavailable.") from exc
        else:
            return _see_other(
                reverse("work-list")
                if record_kind == "work"
                else reverse("work-detail", kwargs={"work_id": work.id})
            )
    return render(
        request,
        "stories/structure_delete.html",
        {"work": work, "record": record, "record_kind": record_kind, "error": error},
        status=409 if error else 200,
    )


def _render_structure_form(
    request: HttpRequest,
    *,
    work: Work,
    form: VolumeForm | ArcForm | ChapterForm,
    heading: str,
    support: str,
    submit_label: str,
    record: Volume | Arc | Chapter | None = None,
    record_kind: str = "",
) -> HttpResponse:
    return render(
        request,
        "stories/structure_form.html",
        {
            "work": work,
            "form": form,
            "heading": heading,
            "support": support,
            "submit_label": submit_label,
            "record": record,
            "record_kind": record_kind,
        },
        status=422 if request.method == "POST" else 200,
    )


def _volume(workspace: Workspace, work: Work, volume_id: uuid.UUID) -> Volume:
    try:
        return cast(Volume, Volume.objects.get(id=volume_id, workspace=workspace, work=work))
    except Volume.DoesNotExist as exc:
        raise Http404("Volume is unavailable.") from exc


def _arc(workspace: Workspace, work: Work, arc_id: uuid.UUID) -> Arc:
    try:
        return cast(Arc, Arc.objects.get(id=arc_id, workspace=workspace, work=work))
    except Arc.DoesNotExist as exc:
        raise Http404("Arc is unavailable.") from exc


def _chapter(workspace: Workspace, work: Work, chapter_id: uuid.UUID) -> Chapter:
    try:
        return cast(
            Chapter,
            Chapter.objects.select_related("volume", "arc", "pov_character").get(
                id=chapter_id, workspace=workspace, work=work
            ),
        )
    except Chapter.DoesNotExist as exc:
        raise Http404("Chapter is unavailable.") from exc


def _chapter_scene(workspace: Workspace, chapter: Chapter, scene_id: uuid.UUID) -> Scene:
    try:
        return cast(
            Scene,
            Scene.objects.select_related("current_revision").get(
                id=scene_id,
                workspace=workspace,
                chapter=chapter,
                lifecycle=Scene.Lifecycle.ACTIVE,
            ),
        )
    except Scene.DoesNotExist as exc:
        raise Http404("Scene is unavailable.") from exc


def _structure_record(
    workspace: Workspace,
    work: Work,
    record_kind: str,
    record_id: uuid.UUID,
) -> Work | Volume | Arc | Chapter:
    if record_kind == "work" and record_id == work.id:
        return work
    models_by_kind: dict[str, type[Volume | Arc | Chapter]] = {
        "volume": Volume,
        "arc": Arc,
        "chapter": Chapter,
    }
    model = models_by_kind.get(record_kind)
    if model is None:
        raise Http404("Structure record is unavailable.")
    try:
        return model.objects.get(id=record_id, workspace=workspace, work=work)
    except model.DoesNotExist as exc:
        raise Http404("Structure record is unavailable.") from exc


def _decorate_work_counts(workspace: Workspace, works: list[Work]) -> None:
    for work in works:
        work.volume_count = Volume.objects.filter(workspace=workspace, work=work).count()
        work.arc_count = Arc.objects.filter(workspace=workspace, work=work).count()
        work.chapter_count = Chapter.objects.filter(workspace=workspace, work=work).count()
        work.scene_count = (
            Scene.objects.filter(workspace=workspace, work=work)
            .exclude(lifecycle=Scene.Lifecycle.TRASHED)
            .count()
        )
