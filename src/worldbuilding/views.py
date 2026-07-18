import uuid
from dataclasses import dataclass
from typing import cast

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Model, Q
from django.db.models.deletion import ProtectedError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from scenes.models import Scene
from workspaces.models import Workspace
from workspaces.services import resolve_owner_workspace
from worldbuilding.forms import (
    CodexEntryForm,
    CreatureForm,
    LocationForm,
    RegionForm,
    SceneWorldContextForm,
    WorldConnectionForm,
    WorldItemForm,
)
from worldbuilding.models import (
    CodexCharacterLink,
    CodexEntry,
    CodexGroupLink,
    CodexLocationLink,
    CodexRegionLink,
    CodexRelation,
    Creature,
    CreatureCharacterLink,
    CreatureCodexLink,
    CreatureGroupLink,
    CreatureLocationLink,
    CreatureRegionLink,
    ItemCharacterLink,
    ItemGroupLink,
    Location,
    LocationCharacterLink,
    LocationGroupLink,
    Region,
    RegionGroupLink,
    SceneCodexLink,
    SceneCreatureLink,
    SceneGroupLink,
    SceneItemLink,
    SceneLocationLink,
    SceneRegionLink,
    WorldItem,
)


@dataclass(frozen=True)
class RecordKind:
    model: type[Model]
    form: type
    label: str
    plural: str
    title_field: str
    search_fields: tuple[str, ...]
    select_related: tuple[str, ...] = ()


KINDS = {
    "locations": RecordKind(
        Location,
        LocationForm,
        "Location",
        "Locations",
        "name",
        (
            "name",
            "aliases",
            "summary",
            "description",
            "history",
            "current_state",
            "atmosphere",
            "notable_features",
            "sensory_notes",
            "hazards",
            "culture",
            "travel_notes",
            "notes",
        ),
        ("region",),
    ),
    "regions": RecordKind(
        Region,
        RegionForm,
        "Region",
        "Regions",
        "name",
        (
            "name",
            "summary",
            "description",
            "geography",
            "climate",
            "cultures",
            "government",
            "notable_features",
            "hazards",
            "notes",
        ),
        ("parent",),
    ),
    "codex": RecordKind(
        CodexEntry,
        CodexEntryForm,
        "Codex entry",
        "Codex",
        "term",
        (
            "term",
            "aliases",
            "definition",
            "description",
            "implications",
            "related_terms",
            "provenance_note",
            "notes",
        ),
    ),
    "items": RecordKind(
        WorldItem,
        WorldItemForm,
        "Item",
        "Items",
        "name",
        (
            "name",
            "aliases",
            "summary",
            "description",
            "appearance",
            "origin",
            "function",
            "capabilities",
            "limitations",
            "costs_dangers",
            "current_condition",
            "notes",
        ),
        ("current_location",),
    ),
    "creatures": RecordKind(
        Creature,
        CreatureForm,
        "Creature",
        "Creatures",
        "name",
        (
            "name",
            "aliases",
            "classification",
            "summary",
            "appearance",
            "biology",
            "habitat",
            "behavior",
            "diet",
            "abilities",
            "weaknesses",
            "signs",
            "ecology",
            "origin",
            "cultural_significance",
            "encounter_notes",
            "notes",
        ),
    ),
}


def _workspace(request: HttpRequest) -> Workspace:
    return resolve_owner_workspace(cast(object, request.user))


def _kind(kind: str) -> RecordKind:
    if kind not in KINDS:
        raise Http404("World library is unavailable.")
    return KINDS[kind]


@never_cache
@login_required
def world_home(request: HttpRequest) -> HttpResponse:
    workspace = _workspace(request)
    panels = []
    for slug, config in KINDS.items():
        queryset = config.model.objects.filter(workspace=workspace).order_by("-updated_at", "id")
        panels.append(
            {
                "slug": slug,
                "label": config.plural,
                "count": queryset.count(),
                "recent": queryset.first(),
            }
        )
    return render(request, "worldbuilding/home.html", {"workspace": workspace, "panels": panels})


@never_cache
@login_required
def world_bible(request: HttpRequest) -> HttpResponse:
    workspace = _workspace(request)
    sections = []
    for slug, config in KINDS.items():
        records = config.model.objects.filter(workspace=workspace).order_by("-updated_at", "id")
        sections.append(
            {
                "slug": slug,
                "label": config.plural,
                "count": records.count(),
                "records": records[:8],
                "title_field": config.title_field,
            }
        )
    from characters.models import CharacterGroup

    return render(
        request,
        "worldbuilding/world_bible.html",
        {
            "workspace": workspace,
            "sections": sections,
            "groups": CharacterGroup.objects.filter(workspace=workspace).order_by("name")[:8],
        },
    )


@never_cache
@login_required
def record_list(request: HttpRequest, kind: str) -> HttpResponse:
    workspace = _workspace(request)
    config = _kind(kind)
    records = config.model.objects.filter(workspace=workspace)
    if config.select_related:
        records = records.select_related(*config.select_related)
    query = request.GET.get("query", "").strip()
    selected_type = request.GET.get("type", "").strip()
    selected_status = request.GET.get("status", "").strip()
    if query:
        predicate = Q()
        for field in config.search_fields:
            predicate |= Q(**{f"{field}__icontains": query})
        records = records.filter(predicate)
    type_field = next(
        (
            name
            for name in ("location_type", "region_type", "category", "item_type", "creature_type")
            if hasattr(config.model, name)
        ),
        None,
    )
    if selected_type and type_field:
        records = records.filter(**{type_field: selected_type})
    if selected_status and hasattr(config.model, "status"):
        records = records.filter(status=selected_status)
    return render(
        request,
        "worldbuilding/list.html",
        {
            "kind": kind,
            "config": config,
            "records": records,
            "query": query,
            "selected_type": selected_type,
            "selected_status": selected_status,
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def record_create(request: HttpRequest, kind: str) -> HttpResponse:
    workspace = _workspace(request)
    config = _kind(kind)
    form = config.form(request.POST or None, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.workspace = workspace
        record.full_clean()
        record.save()
        return redirect("world-record-detail", kind=kind, record_id=record.pk)
    return render(
        request,
        "worldbuilding/form.html",
        {"kind": kind, "config": config, "form": form, "record": None},
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def record_detail(request: HttpRequest, kind: str, record_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    config = _kind(kind)
    try:
        record = config.model.objects.get(pk=record_id, workspace=workspace)
    except config.model.DoesNotExist as exc:
        raise Http404("World record is unavailable.") from exc
    form = config.form(request.POST or None, instance=record, workspace=workspace)
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.full_clean()
        updated.save()
        return redirect("world-record-detail", kind=kind, record_id=record.pk)
    context = {"kind": kind, "config": config, "record": record, "form": form}
    if isinstance(record, Region):
        context.update(children=record.children.all(), locations=record.locations.all())
    context["connection_form"] = WorldConnectionForm(workspace=workspace)
    context["connections"] = _record_connections(kind, record)
    return render(request, "worldbuilding/detail.html", context)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def record_delete(request: HttpRequest, kind: str, record_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    config = _kind(kind)
    try:
        record = config.model.objects.get(pk=record_id, workspace=workspace)
    except config.model.DoesNotExist as exc:
        raise Http404("World record is unavailable.") from exc
    blocked = False
    if request.method == "POST":
        try:
            record.delete()
        except ProtectedError:
            blocked = True
        else:
            return redirect("world-record-list", kind=kind)
    return render(
        request,
        "worldbuilding/delete.html",
        {"kind": kind, "config": config, "record": record, "blocked": blocked},
    )


CONNECTION_MODELS = {
    ("locations", "character"): (LocationCharacterLink, "location", "character"),
    ("locations", "group"): (LocationGroupLink, "location", "group"),
    ("locations", "scene"): (SceneLocationLink, "location", "scene"),
    ("regions", "group"): (RegionGroupLink, "region", "group"),
    ("regions", "scene"): (SceneRegionLink, "region", "scene"),
    ("codex", "character"): (CodexCharacterLink, "codex", "character"),
    ("codex", "group"): (CodexGroupLink, "codex", "group"),
    ("codex", "scene"): (SceneCodexLink, "codex", "scene"),
    ("codex", "location"): (CodexLocationLink, "codex", "location"),
    ("codex", "region"): (CodexRegionLink, "codex", "region"),
    ("items", "character"): (ItemCharacterLink, "item", "character"),
    ("items", "group"): (ItemGroupLink, "item", "group"),
    ("items", "scene"): (SceneItemLink, "item", "scene"),
    ("creatures", "character"): (CreatureCharacterLink, "creature", "character"),
    ("creatures", "group"): (CreatureGroupLink, "creature", "group"),
    ("creatures", "scene"): (SceneCreatureLink, "creature", "scene"),
    ("creatures", "location"): (CreatureLocationLink, "creature", "location"),
    ("creatures", "region"): (CreatureRegionLink, "creature", "region"),
    ("creatures", "codex_entry"): (CreatureCodexLink, "creature", "codex"),
}


@never_cache
@login_required
@require_POST
def record_connection_create(request: HttpRequest, kind: str, record_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    config = _kind(kind)
    try:
        record = config.model.objects.get(pk=record_id, workspace=workspace)
    except config.model.DoesNotExist as exc:
        raise Http404("World record is unavailable.") from exc
    form = WorldConnectionForm(request.POST, workspace=workspace)
    if not form.is_valid():
        raise Http404("World connection is unavailable.")
    targets = ("character", "group", "scene", "location", "region", "codex_entry")
    target_name = next(name for name in targets if form.cleaned_data.get(name))
    if kind == "codex" and target_name == "codex_entry":
        other = form.cleaned_data[target_name]
        source, target = sorted((record, other), key=lambda item: item.id)
        link = CodexRelation(
            workspace=workspace,
            source=source,
            target=target,
            notes=form.cleaned_data["notes"],
        )
    else:
        mapping = CONNECTION_MODELS.get((kind, target_name))
        if not mapping:
            raise Http404("This connection is not supported.")
        model, record_field, target_field = mapping
        link = model(
            workspace=workspace,
            role=form.cleaned_data["role"],
            notes=form.cleaned_data["notes"],
            **{record_field: record, target_field: form.cleaned_data[target_name]},
        )
    try:
        link.full_clean()
        link.save()
    except (ValidationError, IntegrityError) as exc:
        raise Http404("World connection is unavailable.") from exc
    return redirect("world-record-detail", kind=kind, record_id=record.id)


def _record_connections(kind: str, record: Model) -> list[dict[str, object]]:
    connections: list[dict[str, object]] = []
    timeline_links = getattr(record, "timeline_links", None)
    if timeline_links is not None:
        for link in timeline_links.select_related("event"):
            connections.append(
                {
                    "record": (
                        f"Timeline · {link.event.display_date or 'Unknown'} · {link.event.title}"
                    ),
                    "role": link.role,
                }
            )
    for (record_kind, _), (model, record_field, target_field) in CONNECTION_MODELS.items():
        if record_kind != kind:
            continue
        for link in model.objects.filter(**{record_field: record}).select_related(target_field):
            connections.append({"record": getattr(link, target_field), "role": link.role})
    if kind == "codex":
        relations = CodexRelation.objects.filter(
            Q(source=record) | Q(target=record)
        ).select_related("source", "target")
        for relation in relations:
            other = relation.target if relation.source_id == record.id else relation.source
            connections.append({"record": other, "role": "Related lore"})
    return connections


def scene_world_context(scene: Scene) -> dict[str, object]:
    location_links = SceneLocationLink.objects.filter(scene=scene).select_related("location")
    return {
        "primary_location": next(
            (link.location for link in location_links if link.role == "primary"), None
        ),
        "locations": tuple(link.location for link in location_links),
        "regions": tuple(
            link.region
            for link in SceneRegionLink.objects.filter(scene=scene).select_related("region")
        ),
        "groups": tuple(
            link.group
            for link in SceneGroupLink.objects.filter(scene=scene).select_related("group")
        ),
        "codex_entries": tuple(
            link.codex
            for link in SceneCodexLink.objects.filter(scene=scene).select_related("codex")
        ),
        "items": tuple(
            link.item for link in SceneItemLink.objects.filter(scene=scene).select_related("item")
        ),
        "creatures": tuple(
            link.creature
            for link in SceneCreatureLink.objects.filter(scene=scene).select_related("creature")
        ),
    }


@never_cache
@login_required
@require_POST
def scene_world_context_update(request: HttpRequest, scene_id: uuid.UUID) -> HttpResponse:
    workspace = _workspace(request)
    try:
        scene = Scene.objects.get(
            id=scene_id, workspace=workspace, lifecycle=Scene.Lifecycle.ACTIVE
        )
    except Scene.DoesNotExist as exc:
        raise Http404("Scene is unavailable.") from exc
    form = SceneWorldContextForm(request.POST, workspace=workspace)
    if not form.is_valid():
        raise Http404("World context is unavailable.")
    primary = form.cleaned_data["primary_location"]
    locations = set(form.cleaned_data["locations"])
    if primary:
        locations.add(primary)
    mappings = (
        (SceneLocationLink, "location", locations),
        (SceneRegionLink, "region", form.cleaned_data["regions"]),
        (SceneGroupLink, "group", form.cleaned_data["groups"]),
        (SceneCodexLink, "codex", form.cleaned_data["codex_entries"]),
        (SceneItemLink, "item", form.cleaned_data["items"]),
        (SceneCreatureLink, "creature", form.cleaned_data["creatures"]),
    )
    with transaction.atomic():
        for model, field, values in mappings:
            model.objects.filter(scene=scene).delete()
            for value in values:
                link = model(workspace=workspace, scene=scene, **{field: value})
                if model is SceneLocationLink and primary and value.pk == primary.pk:
                    link.role = "primary"
                link.full_clean()
                link.save()
    return redirect("scene-editor", scene_id=scene.id)
