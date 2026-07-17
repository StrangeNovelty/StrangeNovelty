import uuid
from typing import cast

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from scenes.exceptions import LifecycleDisallowsMutation
from scenes.models import Scene
from stories.forms import (
    ArcForm,
    ChapterForm,
    ChapterSceneAttachForm,
    ChapterSceneCreateForm,
    ChapterSceneOrderForm,
    VolumeForm,
    WorkForm,
    WorkSearchForm,
)
from stories.models import Arc, Chapter, Volume, Work
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
    return render(
        request,
        "stories/chapter_detail.html",
        {
            "work": work,
            "chapter": chapter,
            "form": form,
            "writing": writing,
            "scene_create_form": ChapterSceneCreateForm(prefix="new-scene"),
            "scene_attach_form": ChapterSceneAttachForm(
                workspace=workspace, prefix="existing-scene"
            ),
        },
        status=422 if request.method == "POST" else 200,
    )


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
