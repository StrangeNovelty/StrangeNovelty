import hashlib

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from jobs.services import enqueue_job
from publishing.compilation import compile_manuscript, populate_from_work, use_latest_revisions
from publishing.forms import (
    ArtworkPlacementForm,
    ExportReviewForm,
    GlossaryEntryForm,
    ManuscriptEntryForm,
    ManuscriptProjectForm,
    PublicationEntryForm,
)
from publishing.models import ExportRecord, ManuscriptEntry, ManuscriptProject, PublicationEntry
from publishing.profiles import PROFILES
from workspaces.services import resolve_owner_workspace


def workspace(request):
    return resolve_owner_workspace(request.user)


@never_cache
@login_required
def publishing_home(request):
    ws = workspace(request)
    return render(
        request,
        "publishing/home.html",
        {
            "manuscripts": ws.manuscripts.exclude(status="archived")[:8],
            "awaiting_review": ws.manuscripts.filter(status="ready").count(),
            "ready_exports": ws.exports.filter(status="ready")[:5],
            "queued_publications": ws.publication_entries.exclude(
                status__in=("published", "archived", "withdrawn")
            )[:8],
        },
    )


@never_cache
@login_required
def manuscript_list(request):
    records = workspace(request).manuscripts.all()
    if request.GET.get("status"):
        records = records.filter(status=request.GET["status"])
    if request.GET.get("work"):
        records = records.filter(work_id=request.GET["work"])
    return render(
        request,
        "publishing/manuscript_list.html",
        {"manuscripts": records, "statuses": ManuscriptProject.STATUSES},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def manuscript_form(request, manuscript_id=None):
    ws = workspace(request)
    record = (
        get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=ws)
        if manuscript_id
        else None
    )
    form = ManuscriptProjectForm(request.POST or None, instance=record, workspace=ws)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = ws
        record.full_clean()
        record.save()
        return redirect("publishing-manuscript-detail", record.id)
    return render(request, "publishing/form.html", {"form": form, "heading": "Manuscript Project"})


@never_cache
@login_required
def manuscript_detail(request, manuscript_id):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    compiled = compile_manuscript(project)
    return render(
        request,
        "publishing/manuscript_detail.html",
        {"project": project, "compiled": compiled, "profiles": PROFILES},
    )


@login_required
@require_POST
def manuscript_populate(request, manuscript_id):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    populate_from_work(project)
    return redirect("publishing-manuscript-detail", project.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def entry_form(request, manuscript_id, entry_id=None):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    entry = get_object_or_404(ManuscriptEntry, id=entry_id, project=project) if entry_id else None
    form = ManuscriptEntryForm(request.POST or None, instance=entry, project=project)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.project = project
        entry.full_clean()
        entry.save()
        if (
            entry.entry_type == "scene"
            and entry.scene.current_revision_id
            and not hasattr(entry, "scene_selection")
        ):
            from publishing.models import ManuscriptSceneSelection

            ManuscriptSceneSelection.objects.create(
                entry=entry,
                scene=entry.scene,
                selected_revision=entry.scene.current_revision,
                source_checksum=entry.scene.current_revision.content_sha256,
            )
        return redirect("publishing-manuscript-detail", project.id)
    return render(request, "publishing/form.html", {"form": form, "heading": "Manuscript Section"})


@login_required
@require_POST
def revision_action(request, manuscript_id):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    action = request.POST.get("action")
    if action not in ("latest", "lock"):
        raise Http404
    use_latest_revisions(project, lock=action == "lock")
    return redirect("publishing-manuscript-detail", project.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def artwork_placement_form(request, manuscript_id):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    form = ArtworkPlacementForm(request.POST or None, project=project)
    if request.method == "POST" and form.is_valid():
        placement = form.save(commit=False)
        placement.project = project
        placement.full_clean()
        placement.save()
        return redirect("publishing-manuscript-detail", project.id)
    return render(request, "publishing/form.html", {"form": form, "heading": "Manuscript Artwork"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def glossary_entry_form(request, manuscript_id):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    form = GlossaryEntryForm(request.POST or None, project=project)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.project = project
        item.full_clean()
        item.save()
        return redirect("publishing-manuscript-detail", project.id)
    return render(request, "publishing/form.html", {"form": form, "heading": "Glossary Selection"})


@never_cache
@login_required
def reading_preview(request, manuscript_id):
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=workspace(request))
    return render(
        request,
        "publishing/reading_preview.html",
        {
            "project": project,
            "compiled": compile_manuscript(project),
            "section_mode": request.GET.get("mode") == "sections",
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def export_review(request, manuscript_id):
    ws = workspace(request)
    project = get_object_or_404(ManuscriptProject, id=manuscript_id, workspace=ws)
    compiled = compile_manuscript(project)
    form = ExportReviewForm(request.POST or None, initial={"filename": project.name})
    if request.method == "POST" and form.is_valid():
        if compiled.warnings and not form.cleaned_data["proceed_with_warnings"]:
            form.add_error("proceed_with_warnings", "Review the warnings or explicitly continue.")
        else:
            if form.cleaned_data["lock_revisions"]:
                use_latest_revisions(project, lock=True)
                compiled = compile_manuscript(project)
            export = ExportRecord.objects.create(
                workspace=ws,
                project=project,
                export_format=form.cleaned_data["export_format"],
                filename=form.cleaned_data["filename"],
                compiled_manuscript_checksum=compiled.checksum,
                source_snapshot=compiled.source_snapshot,
                warning_report=list(compiled.warnings),
            )
            fingerprint = hashlib.sha256(
                f"{export.id}:{compiled.checksum}:{export.export_format}".encode()
            ).hexdigest()
            result = enqueue_job(
                workspace=ws,
                caller="web",
                caller_reference="publishing-export",
                idempotency_key=f"publish-{export.id}",
                request_fingerprint=fingerprint,
                job_type="generate_manuscript_export",
                target_category="export",
                target_id=export.id,
                projection_version="publishing-export-v1",
            )
            export.job = result.job
            export.save(update_fields=("job",))
            return redirect("publishing-export-detail", export.id)
    return render(
        request,
        "publishing/export_review.html",
        {"project": project, "compiled": compiled, "form": form},
    )


@never_cache
@login_required
def export_list(request):
    records = workspace(request).exports.select_related("project")
    if request.GET.get("format"):
        records = records.filter(export_format=request.GET["format"])
    if request.GET.get("status"):
        records = records.filter(status=request.GET["status"])
    return render(
        request,
        "publishing/export_list.html",
        {"exports": records, "formats": ExportRecord.FORMATS, "statuses": ExportRecord.STATUSES},
    )


@never_cache
@login_required
def export_detail(request, export_id):
    record = get_object_or_404(ExportRecord, id=export_id, workspace=workspace(request))
    return render(request, "publishing/export_detail.html", {"export": record})


@login_required
def export_download(request, export_id):
    record = get_object_or_404(
        ExportRecord, id=export_id, workspace=workspace(request), status="ready"
    )
    if not record.file:
        raise Http404
    try:
        handle = record.file.open("rb")
    except OSError as exc:
        raise Http404("Export unavailable.") from exc
    return FileResponse(
        handle, content_type=record.mime_type, as_attachment=True, filename=record.filename
    )


@login_required
@require_POST
def export_retry(request, export_id):
    ws = workspace(request)
    original = get_object_or_404(ExportRecord, id=export_id, workspace=ws)
    retry = ExportRecord.objects.create(
        workspace=ws,
        project=original.project,
        export_format=original.export_format,
        filename=original.filename,
        source_snapshot=original.source_snapshot,
    )
    fingerprint = hashlib.sha256(f"retry:{retry.id}:{original.id}".encode()).hexdigest()
    result = enqueue_job(
        workspace=ws,
        caller="web",
        caller_reference="publishing-retry",
        idempotency_key=f"retry-export-{retry.id}",
        request_fingerprint=fingerprint,
        job_type="generate_manuscript_export",
        target_category="export",
        target_id=retry.id,
        projection_version="publishing-export-v1",
    )
    retry.job = result.job
    retry.save(update_fields=("job",))
    return redirect("publishing-export-detail", retry.id)


@never_cache
@login_required
def publication_list(request):
    records = workspace(request).publication_entries.select_related(
        "work", "chapter", "manuscript", "export"
    )
    if request.GET.get("status"):
        records = records.filter(status=request.GET["status"])
    return render(
        request,
        "publishing/publication_list.html",
        {"publications": records, "statuses": PublicationEntry.STATUSES},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def publication_form(request, publication_id=None):
    ws = workspace(request)
    record = (
        get_object_or_404(PublicationEntry, id=publication_id, workspace=ws)
        if publication_id
        else None
    )
    form = PublicationEntryForm(request.POST or None, instance=record, workspace=ws)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = ws
        record.full_clean()
        record.save()
        return redirect("publishing-publication-list")
    return render(request, "publishing/form.html", {"form": form, "heading": "Publication Entry"})


@login_required
@require_POST
def publication_transition(request, publication_id):
    record = get_object_or_404(PublicationEntry, id=publication_id, workspace=workspace(request))
    status = request.POST.get("status")
    if status not in dict(PublicationEntry.STATUSES):
        raise Http404
    if status == "published":
        record.published_date = record.published_date or timezone.localdate()
        if record.chapter_id:
            record.revision_snapshot = {
                "scenes": {
                    str(scene.id): str(scene.current_revision_id)
                    for scene in record.chapter.scenes.exclude(lifecycle="trashed")
                }
            }
    record.status = status
    record.save(update_fields=("status", "published_date", "revision_snapshot", "updated_at"))
    return redirect("publishing-publication-list")


@login_required
@require_POST
def batch_web_serial(request):
    ws = workspace(request)
    work = get_object_or_404(ws.works, id=request.POST.get("work"), work_type="web_serial")
    for chapter in work.chapters.order_by("order", "id"):
        PublicationEntry.objects.get_or_create(
            workspace=ws,
            work=work,
            chapter=chapter,
            publication_type="web_serial_chapter",
            defaults={"public_title": chapter.title, "status": "planned"},
        )
    return redirect("publishing-publication-list")
