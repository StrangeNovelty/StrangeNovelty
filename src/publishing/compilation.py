import hashlib
import json
import re
from dataclasses import asdict, dataclass

from django.db import transaction

from publishing.models import ManuscriptEntry, ManuscriptSceneSelection
from publishing.profiles import profile_for


@dataclass(frozen=True, slots=True)
class CompiledSection:
    entry_id: str
    entry_type: str
    heading: str
    paragraphs: tuple[str, ...]
    source_url_name: str
    source_id: str
    page_break_before: bool
    artwork_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledManuscript:
    title: str
    subtitle: str
    author: str
    edition: str
    sections: tuple[CompiledSection, ...]
    word_count: int
    chapter_count: int
    scene_count: int
    reading_minutes: int
    warnings: tuple[str, ...]
    source_snapshot: dict
    checksum: str


def paragraphs(value):
    return tuple(part.strip() for part in re.split(r"\n\s*\n", value or "") if part.strip())


def populate_from_work(project):
    if project.status not in ("draft", "ready"):
        raise ValueError("Approved Manuscripts are not silently repopulated.")
    with transaction.atomic():
        project.entries.all().delete()
        order = 10
        ManuscriptEntry.objects.create(project=project, order=order, entry_type="title_page")
        order += 10
        previous_volume = previous_arc = None
        for chapter in project.work.chapters.select_related("volume", "arc").order_by(
            "order", "id"
        ):
            if chapter.volume_id and chapter.volume_id != previous_volume:
                ManuscriptEntry.objects.create(
                    project=project, order=order, entry_type="volume_heading", volume=chapter.volume
                )
                order += 10
                previous_volume = chapter.volume_id
            if chapter.arc_id and chapter.arc_id != previous_arc:
                ManuscriptEntry.objects.create(
                    project=project, order=order, entry_type="arc_heading", arc=chapter.arc
                )
                order += 10
                previous_arc = chapter.arc_id
            ManuscriptEntry.objects.create(
                project=project, order=order, entry_type="chapter", chapter=chapter
            )
            order += 10
            for scene in (
                chapter.scenes.exclude(lifecycle="trashed")
                .select_related("current_revision")
                .order_by("structure_order", "id")
            ):
                entry = ManuscriptEntry.objects.create(
                    project=project, order=order, entry_type="scene", scene=scene
                )
                order += 10
                if scene.current_revision_id:
                    ManuscriptSceneSelection.objects.create(
                        entry=entry,
                        scene=scene,
                        selected_revision=scene.current_revision,
                        selection_mode="latest",
                        source_checksum=scene.current_revision.content_sha256,
                    )
        return project


def use_latest_revisions(project, *, lock=False):
    if project.status == "approved" and not lock:
        raise ValueError("Approved Manuscripts require an explicit lock operation.")
    for entry in project.entries.filter(entry_type="scene", include=True).select_related(
        "scene__current_revision"
    ):
        if not entry.scene.current_revision_id:
            continue
        selection, _ = ManuscriptSceneSelection.objects.update_or_create(
            entry=entry,
            defaults={
                "scene": entry.scene,
                "selected_revision": entry.scene.current_revision,
                "selection_mode": "locked" if lock else "latest",
                "locked": lock,
                "source_checksum": entry.scene.current_revision.content_sha256,
            },
        )
        selection.full_clean()


def compile_manuscript(project):
    profile = profile_for(project)
    warnings = []
    sections = []
    revision_ids = []
    seen_scenes = set()
    chapter_ids = set()
    scene_count = word_count = 0
    for placement in project.artwork_placements.select_related("artwork"):
        artwork = placement.artwork
        if not artwork.file or not artwork.file.storage.exists(artwork.file.name):
            warnings.append(f"Artwork file unavailable: {artwork.title}")
    for entry in (
        project.entries.filter(include=True)
        .select_related("volume", "arc", "chapter", "scene", "scene__current_revision")
        .prefetch_related("artwork_placements__artwork")
    ):
        heading = entry.custom_heading
        content = entry.custom_text
        source_name = ""
        source_id = ""
        if entry.entry_type == "title_page":
            heading = project.title_override or project.work.title
            content = "\n\n".join(
                filter(
                    None,
                    (
                        project.subtitle_override or project.work.subtitle,
                        project.author_name_override,
                        project.edition_label,
                    ),
                )
            )
        elif entry.entry_type == "volume_heading":
            heading = heading or entry.volume.title
            source_name, source_id = "volume-edit", str(entry.volume_id)
        elif entry.entry_type == "arc_heading":
            heading = heading or entry.arc.title
            source_name, source_id = "arc-edit", str(entry.arc_id)
        elif entry.entry_type == "chapter":
            heading = heading or (
                entry.chapter.label
                if project.include_chapter_labels and entry.chapter.label
                else entry.chapter.title
            )
            content = entry.chapter.summary if project.include_chapter_summaries else content
            chapter_ids.add(entry.chapter_id)
            source_name, source_id = "chapter-detail", str(entry.chapter_id)
        elif entry.entry_type == "scene":
            if entry.scene_id in seen_scenes:
                warnings.append(f"Duplicate Scene excluded: {entry.scene.title}")
                continue
            seen_scenes.add(entry.scene_id)
            try:
                selection = entry.scene_selection
            except ManuscriptSceneSelection.DoesNotExist:
                warnings.append(f"Scene has no Revision selection: {entry.scene.title}")
                continue
            if selection.is_stale:
                warnings.append(f"Newer Revision available: {entry.scene.title}")
            if not selection.selected_revision.content.strip():
                warnings.append(f"Empty Scene: {entry.scene.title}")
            heading = entry.scene.title if project.include_scene_titles else heading
            content = selection.selected_revision.content
            revision_ids.append(str(selection.selected_revision_id))
            scene_count += 1
            source_name, source_id = "scene-editor", str(entry.scene_id)
        elif entry.entry_type == "glossary":
            content = "\n\n".join(
                f"{item.display_name}\n{item.display_summary}"
                for item in project.glossary_entries.all()
            )
        section_paragraphs = paragraphs(content)
        word_count += sum(len(value.split()) for value in section_paragraphs)
        sections.append(
            CompiledSection(
                str(entry.id),
                entry.entry_type,
                heading,
                section_paragraphs,
                source_name,
                source_id,
                entry.page_break_behavior == "before"
                or (profile.chapter_page_break and entry.entry_type == "chapter"),
                tuple(str(item.artwork_id) for item in entry.artwork_placements.all()),
            )
        )
    if not sections:
        warnings.append("The Manuscript has no included sections.")
    snapshot = {
        "workspace_id": str(project.workspace_id),
        "work_id": str(project.work_id),
        "project_id": str(project.id),
        "project_updated_at": project.updated_at.isoformat(),
        "entry_ids": [section.entry_id for section in sections],
        "revision_ids": revision_ids,
        "profile": asdict(profile),
        "artwork": [
            {
                "id": str(use.artwork_id),
                "checksum": use.artwork.checksum,
                "placement": use.placement,
                "entry_id": str(use.entry_id) if use.entry_id else None,
            }
            for use in project.artwork_placements.select_related("artwork")
        ],
    }
    canonical = json.dumps(
        {
            "title": project.title_override or project.work.title,
            "sections": [asdict(item) for item in sections],
            "snapshot": snapshot,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    checksum = hashlib.sha256(canonical.encode()).hexdigest()
    return CompiledManuscript(
        project.title_override or project.work.title,
        project.subtitle_override or project.work.subtitle,
        project.author_name_override,
        project.edition_label,
        tuple(sections),
        word_count,
        len(chapter_ids),
        scene_count,
        max(1, round(word_count / 250)) if word_count else 0,
        tuple(warnings),
        snapshot,
        checksum,
    )
