import pathlib
import uuid

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models

from strange_novelty.private_storage import private_export_storage
from workspaces.models import Workspace


def export_upload_path(instance, filename):
    suffix = pathlib.Path(filename).suffix.lower()[:10]
    return f"publishing/{instance.workspace_id}/{instance.id}{suffix}"


class ManuscriptProject(models.Model):
    TYPES = tuple(
        (value, value.replace("_", " ").title())
        for value in (
            "full_work",
            "volume",
            "arc",
            "chapter_selection",
            "short_story_collection",
            "web_serial_reading_copy",
            "screenplay",
            "stage_play",
            "comic_script",
            "custom",
        )
    )
    STATUSES = (
        ("draft", "Draft"),
        ("ready", "Ready for review"),
        ("approved", "Approved"),
        ("exported", "Exported"),
        ("archived", "Archived"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="manuscripts")
    work = models.ForeignKey("stories.Work", on_delete=models.PROTECT, related_name="manuscripts")
    name = models.CharField(max_length=240)
    manuscript_type = models.CharField(max_length=40, choices=TYPES, default="full_work")
    status = models.CharField(max_length=16, choices=STATUSES, default="draft")
    title_override = models.CharField(max_length=240, blank=True)
    subtitle_override = models.CharField(max_length=240, blank=True)
    author_name_override = models.CharField(max_length=240, blank=True)
    edition_label = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    front_matter_notes = models.TextField(blank=True)
    back_matter_notes = models.TextField(blank=True)
    formatting_profile = models.CharField(max_length=40, default="clean_manuscript")
    formatting_overrides = models.JSONField(default=dict, blank=True)
    include_chapter_labels = models.BooleanField(default=True)
    include_scene_titles = models.BooleanField(default=False)
    include_chapter_summaries = models.BooleanField(default=False)
    include_scene_breaks = models.BooleanField(default=True)
    include_artwork = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")

    def __str__(self):
        return self.name

    def clean(self):
        if self.work_id and self.workspace_id and self.work.workspace_id != self.workspace_id:
            raise ValidationError({"work": "Work must belong to this Workspace."})


class ManuscriptEntry(models.Model):
    TYPES = tuple(
        (value, value.replace("_", " ").title())
        for value in (
            "title_page",
            "copyright_page",
            "dedication",
            "epigraph",
            "table_of_contents",
            "volume_heading",
            "arc_heading",
            "chapter",
            "scene",
            "custom_prose",
            "acknowledgments",
            "author_note",
            "glossary",
            "appendix",
            "other",
        )
    )
    PAGE_BREAKS = (
        ("auto", "Automatic"),
        ("before", "Before"),
        ("after", "After"),
        ("none", "None"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(ManuscriptProject, on_delete=models.CASCADE, related_name="entries")
    order = models.PositiveIntegerField()
    entry_type = models.CharField(max_length=32, choices=TYPES)
    volume = models.ForeignKey("stories.Volume", null=True, blank=True, on_delete=models.PROTECT)
    arc = models.ForeignKey("stories.Arc", null=True, blank=True, on_delete=models.PROTECT)
    chapter = models.ForeignKey("stories.Chapter", null=True, blank=True, on_delete=models.PROTECT)
    scene = models.ForeignKey("scenes.Scene", null=True, blank=True, on_delete=models.PROTECT)
    custom_heading = models.CharField(max_length=240, blank=True)
    custom_text = models.TextField(blank=True)
    include = models.BooleanField(default=True)
    page_break_behavior = models.CharField(max_length=12, choices=PAGE_BREAKS, default="auto")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("project", "order"), name="manuscript_entry_order_unique"
            )
        ]

    def __str__(self):
        return self.custom_heading or self.get_entry_type_display()

    def clean(self):
        records = [self.volume, self.arc, self.chapter, self.scene]
        for record in (item for item in records if item):
            if record.workspace_id != self.project.workspace_id:
                raise ValidationError("Manuscript entries must stay in one Workspace.")
            if getattr(record, "work_id", self.project.work_id) != self.project.work_id:
                raise ValidationError("Manuscript entries must belong to the selected Work.")
        expected = {
            "volume_heading": self.volume,
            "arc_heading": self.arc,
            "chapter": self.chapter,
            "scene": self.scene,
        }
        if self.entry_type in expected and not expected[self.entry_type]:
            raise ValidationError(
                {self.entry_type.removesuffix("_heading"): "This entry requires its source record."}
            )


class ManuscriptSceneSelection(models.Model):
    MODES = (
        ("latest", "Latest current Revision"),
        ("explicit", "Explicit Revision"),
        ("locked", "Locked at export"),
        ("published", "Published Revision"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.OneToOneField(
        ManuscriptEntry, on_delete=models.CASCADE, related_name="scene_selection"
    )
    scene = models.ForeignKey(
        "scenes.Scene", on_delete=models.PROTECT, related_name="manuscript_selections"
    )
    selected_revision = models.ForeignKey(
        "scenes.SceneRevision", on_delete=models.PROTECT, related_name="manuscript_selections"
    )
    selection_mode = models.CharField(max_length=16, choices=MODES, default="latest")
    locked = models.BooleanField(default=False)
    source_checksum = models.CharField(max_length=64)
    selected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.scene} · Revision {self.selected_revision.revision_number}"

    def clean(self):
        if self.entry.entry_type != "scene" or self.entry.scene_id != self.scene_id:
            raise ValidationError("Revision selection must match its Scene entry.")
        if self.selected_revision.scene_id != self.scene_id:
            raise ValidationError(
                {"selected_revision": "Revision must belong to the selected Scene."}
            )
        if self.scene.workspace_id != self.entry.project.workspace_id:
            raise ValidationError("Revision selection must stay in one Workspace.")

    @property
    def is_stale(self):
        return self.scene.current_revision_id != self.selected_revision_id


class ManuscriptArtworkPlacement(models.Model):
    PLACEMENTS = (
        ("cover", "Cover"),
        ("title_page", "Title page"),
        ("chapter", "Chapter illustration"),
        ("map", "Map"),
        ("divider", "Section divider"),
        ("appendix", "Appendix"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        ManuscriptProject, on_delete=models.CASCADE, related_name="artwork_placements"
    )
    artwork = models.ForeignKey(
        "library.ArtworkAsset", on_delete=models.PROTECT, related_name="manuscript_placements"
    )
    entry = models.ForeignKey(
        ManuscriptEntry,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="artwork_placements",
    )
    placement = models.CharField(max_length=20, choices=PLACEMENTS)
    caption = models.CharField(max_length=500, blank=True)
    alt_text_override = models.TextField(blank=True)
    scaling = models.CharField(max_length=20, default="fit")
    page_break_behavior = models.CharField(max_length=12, default="auto")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("project", "artwork", "placement", "entry"),
                nulls_distinct=False,
                name="manuscript_artwork_use_unique",
            )
        ]

    def __str__(self):
        return f"{self.artwork} · {self.get_placement_display()}"

    def clean(self):
        if self.artwork.workspace_id != self.project.workspace_id:
            raise ValidationError("Artwork must belong to the Manuscript Workspace.")
        if self.entry_id and self.entry.project_id != self.project_id:
            raise ValidationError("Artwork entry must belong to this Manuscript.")


class ManuscriptGlossaryEntry(models.Model):
    TARGETS = (
        ("codex", "Codex entry"),
        ("character", "Character"),
        ("group", "Group"),
        ("location", "Location"),
        ("region", "Region"),
        ("item", "Item"),
        ("creature", "Creature"),
        ("timeline_event", "Timeline Event"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        ManuscriptProject, on_delete=models.CASCADE, related_name="glossary_entries"
    )
    target_type = models.CharField(max_length=20, choices=TARGETS)
    target_id = models.UUIDField()
    display_name = models.CharField(max_length=240)
    display_summary = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "display_name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("project", "target_type", "target_id"),
                name="manuscript_glossary_target_unique",
            )
        ]

    def __str__(self):
        return self.display_name

    def clean(self):
        models_by_type = {
            "codex": ("worldbuilding", "CodexEntry"),
            "character": ("characters", "Character"),
            "group": ("characters", "CharacterGroup"),
            "location": ("worldbuilding", "Location"),
            "region": ("worldbuilding", "Region"),
            "item": ("worldbuilding", "WorldItem"),
            "creature": ("worldbuilding", "Creature"),
            "timeline_event": ("timeline", "TimelineEvent"),
        }
        spec = models_by_type.get(self.target_type)
        record = apps.get_model(*spec).objects.filter(id=self.target_id).first() if spec else None
        if not record or record.workspace_id != self.project.workspace_id:
            raise ValidationError({"target_id": "Glossary source must belong to this Workspace."})


class ExportRecord(models.Model):
    FORMATS = (
        ("text", "Plain text"),
        ("markdown", "Markdown"),
        ("html", "HTML"),
        ("docx", "DOCX"),
        ("pdf", "PDF"),
    )
    STATUSES = tuple(
        (value, value.replace("_", " ").title())
        for value in (
            "queued",
            "generating",
            "ready",
            "failed",
            "expired",
            "superseded",
            "archived",
        )
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="exports")
    project = models.ForeignKey(ManuscriptProject, on_delete=models.PROTECT, related_name="exports")
    export_format = models.CharField(max_length=12, choices=FORMATS)
    status = models.CharField(max_length=16, choices=STATUSES, default="queued")
    filename = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=export_upload_path, storage=private_export_storage, blank=True
    )
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    compiled_manuscript_checksum = models.CharField(max_length=64, blank=True)
    source_snapshot = models.JSONField(default=dict)
    warning_report = models.JSONField(default=list)
    job = models.OneToOneField(
        "jobs.Job", null=True, blank=True, on_delete=models.PROTECT, related_name="export_record"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self):
        return self.filename

    def clean(self):
        if self.project_id and (self.project.workspace_id != self.workspace_id):
            raise ValidationError("Export must belong to the Manuscript Workspace.")


class PublicationEntry(models.Model):
    TYPES = tuple(
        (value, value.replace("_", " ").title())
        for value in (
            "web_serial_chapter",
            "short_story",
            "novella",
            "novel",
            "screenplay",
            "comic_issue",
            "collection",
            "private_reading_copy",
            "other",
        )
    )
    STATUSES = tuple(
        (value, value.replace("_", " ").title())
        for value in (
            "planned",
            "drafting",
            "ready",
            "scheduled",
            "published",
            "revised",
            "withdrawn",
            "archived",
        )
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="publication_entries"
    )
    work = models.ForeignKey(
        "stories.Work", on_delete=models.PROTECT, related_name="publication_entries"
    )
    volume = models.ForeignKey("stories.Volume", null=True, blank=True, on_delete=models.PROTECT)
    arc = models.ForeignKey("stories.Arc", null=True, blank=True, on_delete=models.PROTECT)
    chapter = models.ForeignKey(
        "stories.Chapter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="publication_entries",
    )
    manuscript = models.ForeignKey(
        ManuscriptProject,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="publication_entries",
    )
    export = models.ForeignKey(
        ExportRecord,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="publication_entries",
    )
    publication_type = models.CharField(max_length=32, choices=TYPES)
    status = models.CharField(max_length=16, choices=STATUSES, default="planned")
    platform_label = models.CharField(max_length=120, blank=True)
    planned_date = models.DateField(null=True, blank=True)
    published_date = models.DateField(null=True, blank=True)
    public_title = models.CharField(max_length=240)
    public_url = models.URLField(blank=True)
    edition = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    revision_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("planned_date", "created_at", "id")

    def __str__(self):
        return self.public_title

    def clean(self):
        for record in (self.work, self.volume, self.arc, self.chapter):
            if record and record.workspace_id != self.workspace_id:
                raise ValidationError("Publication records must stay in one Workspace.")
        if self.chapter_id and self.chapter.work_id != self.work_id:
            raise ValidationError({"chapter": "Chapter must belong to the selected Work."})
        if self.manuscript_id and self.manuscript.workspace_id != self.workspace_id:
            raise ValidationError({"manuscript": "Manuscript must belong to this Workspace."})
        if self.export_id and self.export.workspace_id != self.workspace_id:
            raise ValidationError({"export": "Export must belong to this Workspace."})

    @property
    def source_changed_after_publication(self):
        if not self.chapter_id or not self.revision_snapshot:
            return False
        current = {
            str(scene.id): str(scene.current_revision_id)
            for scene in self.chapter.scenes.exclude(lifecycle="trashed")
        }
        return current != self.revision_snapshot.get("scenes", {})
