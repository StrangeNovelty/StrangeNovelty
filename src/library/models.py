import pathlib
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from strange_novelty.private_storage import private_upload_storage
from workspaces.models import Workspace


def private_upload_path(instance, filename):
    suffix = pathlib.Path(filename).suffix.lower()[:12]
    kind = "artwork" if isinstance(instance, ArtworkAsset) else "research"
    return f"library/{instance.workspace_id}/{kind}/{instance.id}{suffix}"


class ResearchSource(models.Model):
    TYPES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "book",
            "article",
            "academic_paper",
            "website",
            "interview",
            "documentary",
            "video",
            "podcast",
            "image",
            "map",
            "primary_source",
            "personal_note",
            "reference_document",
            "pdf",
            "other",
        )
    )
    STATUSES = tuple(
        (v, v.title())
        for v in ("unread", "reviewing", "useful", "incorporated", "archived", "rejected")
    )
    EXTRACTION = (
        ("not_requested", "Not requested"),
        ("pending", "Pending"),
        ("extracted", "Extracted"),
        ("failed", "Failed"),
        ("unsupported", "Unsupported"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="research_sources"
    )
    title = models.CharField(max_length=240)
    source_type = models.CharField(max_length=32, choices=TYPES, default="other")
    status = models.CharField(max_length=20, choices=STATUSES, default="unread")
    creator = models.CharField(max_length=240, blank=True)
    publisher = models.CharField(max_length=240, blank=True)
    publication_date_text = models.CharField(max_length=120, blank=True)
    url = models.URLField(blank=True)
    accessed_date = models.DateField(null=True, blank=True)
    citation = models.TextField(blank=True)
    short_summary = models.TextField(blank=True)
    relevance = models.TextField(blank=True)
    credibility_notes = models.TextField(blank=True)
    bias_notes = models.TextField(blank=True)
    usage_rights_notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    source_file = models.FileField(
        upload_to=private_upload_path, storage=private_upload_storage, blank=True
    )
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    extracted_text_status = models.CharField(
        max_length=20, choices=EXTRACTION, default="not_requested"
    )
    extracted_text = models.TextField(blank=True)
    extraction_error = models.CharField(max_length=500, blank=True)
    extraction_checksum = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "checksum"),
                condition=~models.Q(checksum=""),
                name="research_source_workspace_checksum_unique",
            )
        ]

    def __str__(self):
        return self.title


class ResearchNote(models.Model):
    TYPES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "observation",
            "fact",
            "quotation",
            "inspiration",
            "comparison",
            "question",
            "concept",
            "contradiction",
            "sensory_detail",
            "cultural_reference",
            "historical_reference",
            "scientific_reference",
            "craft_note",
            "other",
        )
    )
    STATUSES = (
        ("captured", "Captured"),
        ("developing", "Developing"),
        ("incorporated", "Incorporated"),
        ("partially_incorporated", "Partially incorporated"),
        ("not_for_story", "Not for story use"),
        ("rejected", "Rejected"),
        ("archived", "Archived"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="research_notes"
    )
    source = models.ForeignKey(
        ResearchSource, null=True, blank=True, on_delete=models.PROTECT, related_name="notes"
    )
    title = models.CharField(max_length=240)
    note_type = models.CharField(max_length=32, choices=TYPES, default="observation")
    status = models.CharField(max_length=32, choices=STATUSES, default="captured")
    summary = models.TextField(blank=True)
    note_content = models.TextField(blank=True)
    quotation_excerpt = models.TextField(blank=True)
    page_reference = models.CharField(max_length=240, blank=True)
    interpretation = models.TextField(blank=True)
    story_application = models.TextField(blank=True)
    questions = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")

    def __str__(self):
        return self.title

    def clean(self):
        if self.source_id and self.workspace_id and self.source.workspace_id != self.workspace_id:
            raise ValidationError({"source": "Source must belong to this Workspace."})


class ArtworkAsset(models.Model):
    TYPES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "character_portrait",
            "character_reference",
            "location_art",
            "region_map",
            "world_map",
            "creature_concept",
            "item_concept",
            "faction_emblem",
            "costume",
            "architecture",
            "environment",
            "mood_board",
            "cover_concept",
            "comic_reference",
            "diagram",
            "timeline_graphic",
            "other",
        )
    )
    STATUSES = tuple(
        (v, v.title())
        for v in ("reference", "concept", "draft", "approved", "superseded", "archived")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="artwork_assets"
    )
    title = models.CharField(max_length=240)
    artwork_type = models.CharField(max_length=32, choices=TYPES, default="other")
    status = models.CharField(max_length=20, choices=STATUSES, default="reference")
    description = models.TextField(blank=True)
    creator_source = models.CharField(max_length=240, blank=True)
    source_url = models.URLField(blank=True)
    usage_rights_notes = models.TextField(blank=True)
    file = models.FileField(upload_to=private_upload_path, storage=private_upload_storage)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    alt_text = models.TextField(blank=True)
    visual_notes = models.TextField(blank=True)
    palette_notes = models.TextField(blank=True)
    mood = models.CharField(max_length=240, blank=True)
    tags = models.JSONField(default=list, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "checksum"), name="art_workspace_checksum_unique"
            )
        ]

    def __str__(self):
        return self.title


class ArtworkRelation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        ArtworkAsset, on_delete=models.CASCADE, related_name="outgoing_relations"
    )
    target = models.ForeignKey(
        ArtworkAsset, on_delete=models.PROTECT, related_name="incoming_relations"
    )
    relation_type = models.CharField(max_length=40)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "target", "relation_type"), name="art_relation_unique"
            )
        ]

    def __str__(self):
        return f"{self.source} · {self.relation_type} · {self.target}"

    def clean(self):
        if self.source_id == self.target_id:
            raise ValidationError("Artwork cannot relate to itself.")
        if (
            self.source_id
            and self.target_id
            and self.source.workspace_id != self.target.workspace_id
        ):
            raise ValidationError("Artwork relation must stay in one Workspace.")


class LibraryCollection(models.Model):
    TYPES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "research_folder",
            "mood_board",
            "character_board",
            "location_board",
            "creature_board",
            "item_board",
            "work_reference",
            "chapter_reference",
            "visual_style",
            "historical_period",
            "scientific_topic",
            "other",
        )
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="library_collections"
    )
    name = models.CharField(max_length=240)
    collection_type = models.CharField(max_length=32, choices=TYPES, default="research_folder")
    status = models.CharField(
        max_length=16,
        choices=(("active", "Active"), ("draft", "Draft"), ("archived", "Archived")),
        default="active",
    )
    description = models.TextField(blank=True)
    work = models.ForeignKey(
        "stories.Work",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_collections",
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name", "id")

    def __str__(self):
        return self.name

    def clean(self):
        if self.work_id and self.work.workspace_id != self.workspace_id:
            raise ValidationError({"work": "Work must belong to this Workspace."})


class CollectionMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection = models.ForeignKey(
        LibraryCollection, on_delete=models.CASCADE, related_name="memberships"
    )
    source = models.ForeignKey(ResearchSource, null=True, blank=True, on_delete=models.CASCADE)
    note = models.ForeignKey(ResearchNote, null=True, blank=True, on_delete=models.CASCADE)
    artwork = models.ForeignKey(ArtworkAsset, null=True, blank=True, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ("-pinned", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("collection", "source", "note", "artwork"),
                nulls_distinct=False,
                name="collection_member_unique",
            )
        ]

    def __str__(self):
        return f"{self.collection} membership"

    def clean(self):
        records = [v for v in (self.source, self.note, self.artwork) if v]
        if len(records) != 1:
            raise ValidationError("Select exactly one Library item.")
        if records[0].workspace_id != self.collection.workspace_id:
            raise ValidationError("Collection membership must stay in one Workspace.")


class LibraryConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="library_connections"
    )
    source = models.ForeignKey(
        ResearchSource, null=True, blank=True, on_delete=models.CASCADE, related_name="connections"
    )
    note = models.ForeignKey(
        ResearchNote, null=True, blank=True, on_delete=models.CASCADE, related_name="connections"
    )
    artwork = models.ForeignKey(
        ArtworkAsset, null=True, blank=True, on_delete=models.CASCADE, related_name="connections"
    )
    collection = models.ForeignKey(
        LibraryCollection,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="connections",
    )
    work = models.ForeignKey(
        "stories.Work",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    volume = models.ForeignKey(
        "stories.Volume",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    arc = models.ForeignKey(
        "stories.Arc",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    chapter = models.ForeignKey(
        "stories.Chapter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    scene = models.ForeignKey(
        "scenes.Scene",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    group = models.ForeignKey(
        "characters.CharacterGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    ability = models.ForeignKey(
        "characters.Ability",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    location = models.ForeignKey(
        "worldbuilding.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    region = models.ForeignKey(
        "worldbuilding.Region",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    codex = models.ForeignKey(
        "worldbuilding.CodexEntry",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    item = models.ForeignKey(
        "worldbuilding.WorldItem",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    creature = models.ForeignKey(
        "worldbuilding.Creature",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    thread = models.ForeignKey(
        "continuity.PlotThread",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    secret = models.ForeignKey(
        "continuity.Secret",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    timeline_event = models.ForeignKey(
        "timeline.TimelineEvent",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    draw = models.ForeignKey(
        "decks.SavedDraw",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    interpretation = models.ForeignKey(
        "decks.DrawInterpretation",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    context_pack = models.ForeignKey(
        "ai_assistance.AIContextPack",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="library_connections",
    )
    role = models.CharField(max_length=40, default="other")
    caption = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    LIBRARY_FIELDS = ("source", "note", "artwork", "collection")
    TARGET_FIELDS = (
        "work",
        "volume",
        "arc",
        "chapter",
        "scene",
        "character",
        "group",
        "ability",
        "location",
        "region",
        "codex",
        "item",
        "creature",
        "thread",
        "secret",
        "timeline_event",
        "draw",
        "interpretation",
        "context_pack",
    )

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return f"Library connection · {self.role}"

    def clean(self):
        items = [getattr(self, f) for f in self.LIBRARY_FIELDS if getattr(self, f)]
        targets = [getattr(self, f) for f in self.TARGET_FIELDS if getattr(self, f)]
        if len(items) != 1 or len(targets) != 1:
            raise ValidationError("Select exactly one Library item and one story target.")

        def ws(record):
            return (
                getattr(record, "workspace_id", None)
                or getattr(getattr(record, "thread", None), "workspace_id", None)
                or getattr(getattr(record, "draw", None), "workspace_id", None)
            )

        if items[0].workspace_id != self.workspace_id or ws(targets[0]) != self.workspace_id:
            raise ValidationError("Library connections must stay in one Workspace.")
