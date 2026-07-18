from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from library.forms import ArtworkForm, CollectionForm, MembershipForm, NoteForm, SourceForm
from library.models import (
    ArtworkAsset,
    LibraryCollection,
    LibraryConnection,
    ResearchNote,
    ResearchSource,
)
from library.services import extract_source_text
from strange_novelty.file_delivery import PrivateObjectUnavailable, open_private_object
from workspaces.services import resolve_owner_workspace


def workspace(request):
    return resolve_owner_workspace(request.user)


@never_cache
@login_required
def library_home(request):
    ws = workspace(request)
    return render(
        request,
        "library/home.html",
        {
            "source_count": ws.research_sources.count(),
            "note_count": ws.research_notes.count(),
            "artwork_count": ws.artwork_assets.count(),
            "collection_count": ws.library_collections.count(),
            "unreviewed_count": ws.research_sources.filter(
                status__in=("unread", "reviewing")
            ).count(),
            "recent_sources": ws.research_sources.all()[:5],
            "recent_artwork": ws.artwork_assets.all()[:5],
            "orphan_artwork": ws.artwork_assets.annotate(link_count=Count("connections")).filter(
                link_count=0
            )[:5],
            "sources_without_notes": ws.research_sources.annotate(note_count=Count("notes")).filter(
                note_count=0
            )[:5],
            "collections": ws.library_collections.exclude(status="archived")[:6],
        },
    )


@never_cache
@login_required
def source_list(request):
    ws = workspace(request)
    sources = ws.research_sources.annotate(
        note_count=Count("notes"), connection_count=Count("connections")
    )
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status")
    source_type = request.GET.get("type")
    creator = request.GET.get("creator", "").strip()
    tag = request.GET.get("tag", "").strip()
    if query:
        sources = sources.filter(
            Q(title__icontains=query)
            | Q(creator__icontains=query)
            | Q(citation__icontains=query)
            | Q(short_summary__icontains=query)
            | Q(extracted_text__icontains=query)
        )
    if status:
        sources = sources.filter(status=status)
    if source_type:
        sources = sources.filter(source_type=source_type)
    if creator:
        sources = sources.filter(creator__icontains=creator)
    if tag:
        sources = sources.filter(tags__contains=[tag])
    if request.GET.get("has_file"):
        sources = sources.exclude(source_file="")
    return render(
        request,
        "library/source_list.html",
        {"sources": sources, "statuses": ResearchSource.STATUSES, "types": ResearchSource.TYPES},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def source_form(request, source_id=None):
    ws = workspace(request)
    source = get_object_or_404(ResearchSource, id=source_id, workspace=ws) if source_id else None
    form = SourceForm(request.POST or None, request.FILES or None, instance=source)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = ws
        metadata = getattr(form, "upload_metadata", None)
        if metadata:
            if (
                ws.research_sources.filter(checksum=metadata["checksum"])
                .exclude(id=record.id)
                .exists()
            ):
                form.add_error("source_file", "This file is already in the Library.")
            else:
                record.original_filename = metadata["original_filename"]
                record.mime_type = metadata["mime_type"]
                record.file_size = metadata["size"]
                record.checksum = metadata["checksum"]
        if not form.errors:
            record.full_clean()
            record.save()
            if form.cleaned_data["extract_now"]:
                extract_source_text(record)
            return redirect("library-source-detail", record.id)
    return render(request, "library/form.html", {"form": form, "heading": "Research Source"})


@never_cache
@login_required
def source_detail(request, source_id):
    source = get_object_or_404(ResearchSource, id=source_id, workspace=workspace(request))
    return render(request, "library/source_detail.html", {"source": source})


@login_required
def source_file(request, source_id):
    source = get_object_or_404(ResearchSource, id=source_id, workspace=workspace(request))
    if not source.source_file:
        raise Http404
    try:
        handle = open_private_object(source.source_file)
    except PrivateObjectUnavailable as exc:
        raise Http404("File unavailable.") from exc
    return FileResponse(
        handle,
        content_type=source.mime_type or "application/octet-stream",
        as_attachment=True,
        filename=source.original_filename,
    )


@login_required
@require_POST
def source_extract(request, source_id):
    source = get_object_or_404(ResearchSource, id=source_id, workspace=workspace(request))
    extract_source_text(source)
    return redirect("library-source-detail", source.id)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def note_form(request, note_id=None):
    ws = workspace(request)
    note = get_object_or_404(ResearchNote, id=note_id, workspace=ws) if note_id else None
    form = NoteForm(
        request.POST or None,
        instance=note,
        workspace=ws,
        initial={
            "source": request.GET.get("source"),
            "quotation_excerpt": request.GET.get("excerpt", "")[:5000],
        },
    )
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = ws
        record.full_clean()
        record.save()
        return redirect("library-note-edit", record.id)
    return render(
        request, "library/form.html", {"form": form, "heading": "Research Note", "note": note}
    )


@never_cache
@login_required
def artwork_list(request):
    ws = workspace(request)
    records = ws.artwork_assets.annotate(connection_count=Count("connections"))
    query = request.GET.get("q", "").strip()
    if query:
        records = records.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(alt_text__icontains=query)
            | Q(mood__icontains=query)
        )
    if request.GET.get("type"):
        records = records.filter(artwork_type=request.GET["type"])
    if request.GET.get("status"):
        records = records.filter(status=request.GET["status"])
    if request.GET.get("primary"):
        records = records.filter(is_primary=True)
    return render(
        request,
        "library/artwork_list.html",
        {"artwork": records, "types": ArtworkAsset.TYPES, "statuses": ArtworkAsset.STATUSES},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def artwork_form(request, artwork_id=None):
    ws = workspace(request)
    artwork = get_object_or_404(ArtworkAsset, id=artwork_id, workspace=ws) if artwork_id else None
    form = ArtworkForm(request.POST or None, request.FILES or None, instance=artwork)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = ws
        metadata = getattr(form, "upload_metadata", None)
        if metadata:
            if (
                ws.artwork_assets.filter(checksum=metadata["checksum"])
                .exclude(id=record.id)
                .exists()
            ):
                form.add_error("file", "This image is already in the Library.")
            else:
                for name in (
                    "original_filename",
                    "mime_type",
                    "size",
                    "checksum",
                    "width",
                    "height",
                ):
                    setattr(record, name, metadata[name])
        if not form.errors:
            record.full_clean()
            record.save()
            return redirect("library-artwork-detail", record.id)
    return render(request, "library/form.html", {"form": form, "heading": "Artwork Asset"})


@never_cache
@login_required
def artwork_detail(request, artwork_id):
    record = get_object_or_404(ArtworkAsset, id=artwork_id, workspace=workspace(request))
    return render(request, "library/artwork_detail.html", {"artwork": record})


@login_required
def artwork_file(request, artwork_id):
    record = get_object_or_404(ArtworkAsset, id=artwork_id, workspace=workspace(request))
    try:
        handle = open_private_object(record.file)
    except PrivateObjectUnavailable as exc:
        raise Http404("Image unavailable.") from exc
    return FileResponse(handle, content_type=record.mime_type, filename=record.original_filename)


@never_cache
@login_required
def collection_list(request):
    return render(
        request,
        "library/collection_list.html",
        {"collections": workspace(request).library_collections.all()},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def collection_form(request, collection_id=None):
    ws = workspace(request)
    collection = (
        get_object_or_404(LibraryCollection, id=collection_id, workspace=ws)
        if collection_id
        else None
    )
    form = CollectionForm(request.POST or None, instance=collection, workspace=ws)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = ws
        record.full_clean()
        record.save()
        return redirect("library-collection-detail", record.id)
    return render(request, "library/form.html", {"form": form, "heading": "Library Collection"})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def collection_detail(request, collection_id):
    ws = workspace(request)
    collection = get_object_or_404(LibraryCollection, id=collection_id, workspace=ws)
    form = MembershipForm(request.POST or None, workspace=ws)
    form.instance.collection = collection
    if request.method == "POST" and form.is_valid():
        member = form.save(commit=False)
        try:
            member.full_clean()
            member.save()
        except ValidationError, IntegrityError:
            form.add_error(None, "That item is already in this Collection or is invalid.")
        else:
            return redirect("library-collection-detail", collection.id)
    return render(
        request, "library/collection_detail.html", {"collection": collection, "form": form}
    )


@login_required
@require_POST
def transition(request, kind, record_id):
    ws = workspace(request)
    models = {
        "source": ResearchSource,
        "note": ResearchNote,
        "artwork": ArtworkAsset,
        "collection": LibraryCollection,
    }
    model = models.get(kind)
    if not model:
        raise Http404
    record = get_object_or_404(model, id=record_id, workspace=ws)
    status = request.POST.get("status")
    if status not in dict(record._meta.get_field("status").choices):
        raise Http404
    record.status = status
    record.save(update_fields=("status", "updated_at"))
    return redirect("library-home")


TARGETS = {
    "work": ("stories", "Work"),
    "volume": ("stories", "Volume"),
    "arc": ("stories", "Arc"),
    "chapter": ("stories", "Chapter"),
    "scene": ("scenes", "Scene"),
    "character": ("characters", "Character"),
    "group": ("characters", "CharacterGroup"),
    "ability": ("characters", "Ability"),
    "location": ("worldbuilding", "Location"),
    "region": ("worldbuilding", "Region"),
    "codex": ("worldbuilding", "CodexEntry"),
    "item": ("worldbuilding", "WorldItem"),
    "creature": ("worldbuilding", "Creature"),
    "thread": ("continuity", "PlotThread"),
    "secret": ("continuity", "Secret"),
    "timeline_event": ("timeline", "TimelineEvent"),
    "draw": ("decks", "SavedDraw"),
    "interpretation": ("decks", "DrawInterpretation"),
    "context_pack": ("ai_assistance", "AIContextPack"),
}
ITEMS = {
    "source": ResearchSource,
    "note": ResearchNote,
    "artwork": ArtworkAsset,
    "collection": LibraryCollection,
}


@login_required
@require_POST
def connection_create(request, kind, item_id):
    ws = workspace(request)
    item_model = ITEMS.get(kind)
    target_kind = request.POST.get("target_type")
    spec = TARGETS.get(target_kind)
    if not item_model or not spec:
        raise Http404
    item = get_object_or_404(item_model, id=item_id, workspace=ws)
    target_model = apps.get_model(*spec)
    target = target_model.objects.filter(id=request.POST.get("target_id")).first()
    if not target:
        raise Http404
    link = LibraryConnection(
        workspace=ws,
        role=request.POST.get("role", "other")[:40],
        caption=request.POST.get("caption", "")[:500],
        **{kind: item, target_kind: target},
    )
    link.full_clean()
    if LibraryConnection.objects.filter(
        workspace=ws,
        role=link.role,
        **{kind: item, target_kind: target},
    ).exists():
        raise ValidationError("That Library connection already exists.")
    link.save()
    return redirect("library-home")
