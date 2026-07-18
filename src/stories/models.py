import uuid
from typing import cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from workspaces.models import Workspace


class Work(models.Model):
    class WorkType(models.TextChoices):
        WEB_SERIAL = "web_serial", "Web serial"
        NOVEL = "novel", "Novel"
        NOVELLA = "novella", "Novella"
        SHORT_STORY = "short_story", "Short story"
        SCREENPLAY = "screenplay", "Screenplay"
        STAGE_PLAY = "stage_play", "Stage play"
        COMIC = "comic", "Comic"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        IDEA = "idea", "Idea"
        PLANNING = "planning", "Planning"
        DRAFTING = "drafting", "Drafting"
        REVISING = "revising", "Revising"
        COMPLETE = "complete", "Complete"
        HIATUS = "hiatus", "Hiatus"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="works")
    title = models.CharField(max_length=240)
    subtitle = models.CharField(max_length=240, blank=True)
    work_type = models.CharField(max_length=20, choices=WorkType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IDEA)
    premise = models.TextField(blank=True)
    description = models.TextField(blank=True)
    intended_audience = models.CharField(max_length=240, blank=True)
    genre_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="work_title_contains_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(
                    work_type__in=(
                        "web_serial",
                        "novel",
                        "novella",
                        "short_story",
                        "screenplay",
                        "stage_play",
                        "comic",
                        "other",
                    )
                ),
                name="work_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "idea",
                        "planning",
                        "drafting",
                        "revising",
                        "complete",
                        "hiatus",
                        "archived",
                    )
                ),
                name="work_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "-updated_at"), name="work_ws_updated_idx"),
            models.Index(fields=("workspace", "status"), name="work_ws_status_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.title, str) or self.title != self.title.strip() or not self.title:
            raise ValidationError({"title": "Work title must be present and trimmed."})


class Volume(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETE = "complete", "Complete"
        HIATUS = "hiatus", "Hiatus"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="volumes")
    work = models.ForeignKey(Work, on_delete=models.PROTECT, related_name="volumes")
    title = models.CharField(max_length=240)
    order = models.PositiveBigIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="volume_title_contains_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(status__in=("planned", "active", "complete", "hiatus", "archived")),
                name="volume_status_valid",
            ),
            models.UniqueConstraint(fields=("work", "order"), name="unique_volume_order_in_work"),
        ]
        indexes = [
            models.Index(fields=("workspace", "work", "order"), name="volume_ws_work_order_idx")
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        errors = _title_errors(self.title)
        if self.workspace_id and self.work_id and self.work.workspace_id != self.workspace_id:
            errors["work"] = "Volume Work must belong to this Workspace."
        if errors:
            raise ValidationError(errors)


class Arc(models.Model):
    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETE = "complete", "Complete"
        HIATUS = "hiatus", "Hiatus"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="arcs")
    work = models.ForeignKey(Work, on_delete=models.PROTECT, related_name="arcs")
    volume = models.ForeignKey(
        Volume, on_delete=models.PROTECT, null=True, blank=True, related_name="arcs"
    )
    title = models.CharField(max_length=240)
    order = models.PositiveBigIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    summary = models.TextField(blank=True)
    purpose = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="arc_title_contains_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(status__in=("planned", "active", "complete", "hiatus", "archived")),
                name="arc_status_valid",
            ),
            models.UniqueConstraint(fields=("work", "order"), name="unique_arc_order_in_work"),
        ]
        indexes = [
            models.Index(fields=("workspace", "work", "order"), name="arc_ws_work_order_idx")
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        errors = _title_errors(self.title)
        if self.workspace_id and self.work_id and self.work.workspace_id != self.workspace_id:
            errors["work"] = "Arc Work must belong to this Workspace."
        if self.volume_id and (
            self.volume.workspace_id != self.workspace_id or self.volume.work_id != self.work_id
        ):
            errors["volume"] = "Arc Volume must belong to the selected Work and Workspace."
        if errors:
            raise ValidationError(errors)


class Chapter(models.Model):
    class Status(models.TextChoices):
        BRAINSTORM = "brainstorm", "Brainstorm"
        OUTLINING = "outlining", "Outlining"
        DRAFTING = "drafting", "Drafting"
        REVISING = "revising", "Revising"
        POLISHED = "polished", "Polished"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="chapters")
    work = models.ForeignKey(Work, on_delete=models.PROTECT, related_name="chapters")
    volume = models.ForeignKey(
        Volume, on_delete=models.PROTECT, null=True, blank=True, related_name="chapters"
    )
    arc = models.ForeignKey(
        Arc, on_delete=models.PROTECT, null=True, blank=True, related_name="chapters"
    )
    title = models.CharField(max_length=240)
    label = models.CharField(max_length=120, blank=True)
    order = models.PositiveBigIntegerField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.BRAINSTORM)
    summary = models.TextField(blank=True)
    concept = models.TextField(blank=True)
    goal = models.TextField(blank=True)
    key_beats = models.TextField(blank=True)
    emotional_arc = models.TextField(blank=True)
    character_focus = models.TextField(blank=True)
    brain_dump = models.TextField(blank=True)
    outline = models.TextField(blank=True)
    pov_character = models.ForeignKey(
        "characters.Character",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pov_chapters",
    )
    notes = models.TextField(blank=True)
    editorial_concerns = models.TextField(blank=True)
    revision_priorities = models.TextField(blank=True)
    unresolved_questions = models.TextField(blank=True)
    final_check_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="chapter_title_contains_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "brainstorm",
                        "outlining",
                        "drafting",
                        "revising",
                        "polished",
                        "published",
                        "archived",
                    )
                ),
                name="chapter_status_valid",
            ),
            models.UniqueConstraint(fields=("work", "order"), name="unique_chapter_order_in_work"),
        ]
        indexes = [
            models.Index(fields=("workspace", "work", "order"), name="chapter_ws_work_order_idx")
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        errors = _title_errors(self.title)
        if self.workspace_id and self.work_id and self.work.workspace_id != self.workspace_id:
            errors["work"] = "Chapter Work must belong to this Workspace."
        if self.volume_id and (
            self.volume.workspace_id != self.workspace_id or self.volume.work_id != self.work_id
        ):
            errors["volume"] = "Chapter Volume must belong to the selected Work and Workspace."
        if self.arc_id and (
            self.arc.workspace_id != self.workspace_id or self.arc.work_id != self.work_id
        ):
            errors["arc"] = "Chapter Arc must belong to the selected Work and Workspace."
        if self.arc_id and self.arc.volume_id and self.volume_id != self.arc.volume_id:
            errors["volume"] = "Chapter Volume must match the selected Arc’s Volume."
        if self.pov_character_id and self.pov_character.workspace_id != self.workspace_id:
            errors["pov_character"] = "POV Character must belong to this Workspace."
        if errors:
            raise ValidationError(errors)


class ChapterBeat(models.Model):
    class BeatType(models.TextChoices):
        OPENING = "opening", "Opening"
        SETUP = "setup", "Setup"
        ESCALATION = "escalation", "Escalation"
        DISCOVERY = "discovery", "Discovery"
        CONFRONTATION = "confrontation", "Confrontation"
        REVERSAL = "reversal", "Reversal"
        DECISION = "decision", "Decision"
        REVELATION = "revelation", "Revelation"
        EMOTIONAL_TURN = "emotional_turn", "Emotional turn"
        ACTION = "action", "Action"
        TRANSITION = "transition", "Transition"
        CLIMAX = "climax", "Climax"
        AFTERMATH = "aftermath", "Aftermath"
        HOOK = "hook", "Hook"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        DRAFTED = "drafted", "Drafted"
        REPRESENTED = "represented", "Represented in Scene"
        REVISED = "revised", "Revised"
        CUT = "cut", "Cut"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="structured_beats")
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=240)
    beat_type = models.CharField(max_length=24, choices=BeatType.choices, default=BeatType.OTHER)
    summary = models.TextField(blank=True)
    purpose = models.TextField(blank=True)
    pov_character = models.ForeignKey(
        "characters.Character",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="chapter_beats",
    )
    intended_scene = models.ForeignKey(
        "scenes.Scene",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chapter_beats",
    )
    timeline_event = models.ForeignKey(
        "timeline.TimelineEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chapter_beats",
    )
    emotional_direction = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PLANNED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("chapter", "order"), name="unique_beat_order")
        ]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        errors = {}
        if self.pov_character_id and self.pov_character.workspace_id != self.chapter.workspace_id:
            errors["pov_character"] = "POV Character must belong to this Workspace."
        if self.intended_scene_id and (
            self.intended_scene.workspace_id != self.chapter.workspace_id
            or self.intended_scene.chapter_id != self.chapter_id
        ):
            errors["intended_scene"] = "Intended Scene must belong to this Chapter."
        if self.timeline_event_id and self.timeline_event.workspace_id != self.chapter.workspace_id:
            errors["timeline_event"] = "Timeline Event must belong to this Workspace."
        if errors:
            raise ValidationError(errors)


class SceneBrief(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        SUPERSEDED = "superseded", "Superseded"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey("scenes.Scene", on_delete=models.CASCADE, related_name="briefs")
    source_revision = models.ForeignKey(
        "scenes.SceneRevision", on_delete=models.PROTECT, related_name="scene_briefs"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    pov = models.CharField(max_length=240, blank=True)
    scene_function = models.TextField(blank=True)
    previous_context_summary = models.TextField(blank=True)
    character_wants = models.TextField(blank=True)
    primary_conflict = models.TextField(blank=True)
    stakes = models.TextField(blank=True)
    setting = models.TextField(blank=True)
    atmosphere = models.TextField(blank=True)
    blocking_and_beats = models.TextField(blank=True)
    emotional_movement = models.TextField(blank=True)
    continuity_concerns = models.TextField(blank=True)
    thread_and_clue_opportunities = models.TextField(blank=True)
    opening_beat = models.TextField(blank=True)
    ending_hook = models.TextField(blank=True)
    symbolism = models.TextField(blank=True)
    author_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("scene",), condition=Q(status="active"), name="one_active_scene_brief"
            )
        ]

    def __str__(self) -> str:
        return f"{self.scene}: {self.get_status_display()} Brief"

    @property
    def is_stale(self) -> bool:
        return self.scene.current_revision_id != self.source_revision_id

    def clean(self) -> None:
        if self.source_revision_id and (
            self.source_revision.scene_id != self.scene_id
            or self.source_revision.workspace_id != self.scene.workspace_id
        ):
            raise ValidationError({"source_revision": "Source Revision must belong to this Scene."})


class ChapterPacingProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.OneToOneField(Chapter, on_delete=models.CASCADE, related_name="pacing_profile")
    tension_score = models.PositiveSmallIntegerField(null=True, blank=True)
    tension_notes = models.TextField(blank=True)
    dread_score = models.PositiveSmallIntegerField(null=True, blank=True)
    dread_notes = models.TextField(blank=True)
    emotional_intimacy_score = models.PositiveSmallIntegerField(null=True, blank=True)
    emotional_intimacy_notes = models.TextField(blank=True)
    relationship_tension_score = models.PositiveSmallIntegerField(null=True, blank=True)
    relationship_tension_notes = models.TextField(blank=True)
    pacing_energy_score = models.PositiveSmallIntegerField(null=True, blank=True)
    pacing_energy_notes = models.TextField(blank=True)
    humor_score = models.PositiveSmallIntegerField(null=True, blank=True)
    humor_notes = models.TextField(blank=True)
    action_intensity_score = models.PositiveSmallIntegerField(null=True, blank=True)
    action_intensity_notes = models.TextField(blank=True)
    mystery_pressure_score = models.PositiveSmallIntegerField(null=True, blank=True)
    mystery_pressure_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(tension_score__range=(1, 10)) | Q(tension_score__isnull=True),
                name="pacing_tension_1_10",
            ),
            models.CheckConstraint(
                condition=Q(dread_score__range=(1, 10)) | Q(dread_score__isnull=True),
                name="pacing_dread_1_10",
            ),
            models.CheckConstraint(
                condition=Q(emotional_intimacy_score__range=(1, 10))
                | Q(emotional_intimacy_score__isnull=True),
                name="pacing_intimacy_1_10",
            ),
            models.CheckConstraint(
                condition=Q(relationship_tension_score__range=(1, 10))
                | Q(relationship_tension_score__isnull=True),
                name="pacing_relationship_1_10",
            ),
            models.CheckConstraint(
                condition=Q(pacing_energy_score__range=(1, 10))
                | Q(pacing_energy_score__isnull=True),
                name="pacing_energy_1_10",
            ),
            models.CheckConstraint(
                condition=Q(humor_score__range=(1, 10)) | Q(humor_score__isnull=True),
                name="pacing_humor_1_10",
            ),
            models.CheckConstraint(
                condition=Q(action_intensity_score__range=(1, 10))
                | Q(action_intensity_score__isnull=True),
                name="pacing_action_1_10",
            ),
            models.CheckConstraint(
                condition=Q(mystery_pressure_score__range=(1, 10))
                | Q(mystery_pressure_score__isnull=True),
                name="pacing_mystery_1_10",
            ),
        ]

    def __str__(self) -> str:
        return f"Pacing: {self.chapter}"

    def clean(self) -> None:
        errors = {}
        for field in PACING_SCORE_FIELDS:
            value = getattr(self, field)
            if value is not None and not 1 <= value <= 10:
                errors[field] = "Score must be between 1 and 10."
        if errors:
            raise ValidationError(errors)


PACING_SCORE_FIELDS = (
    "tension_score",
    "dread_score",
    "emotional_intimacy_score",
    "relationship_tension_score",
    "pacing_energy_score",
    "humor_score",
    "action_intensity_score",
    "mystery_pressure_score",
)


class ChapterPlanningSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="planning_snapshots"
    )
    label = models.CharField(max_length=240)
    trigger = models.CharField(max_length=32, default="manual")
    planning_content = models.JSONField(default=dict)
    beat_data = models.JSONField(default=list)
    pacing_data = models.JSONField(default=dict)
    source_ai_request_id = models.UUIDField(null=True, blank=True)
    source_ai_suggestion_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self) -> str:
        return self.label


class ChapterChecklistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="checklist_items")
    label = models.CharField(max_length=240)
    completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("chapter", "order"), name="unique_checklist_order")
        ]

    def __str__(self) -> str:
        return self.label


class WritingDelta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="writing_deltas"
    )
    work = models.ForeignKey(
        Work, null=True, blank=True, on_delete=models.PROTECT, related_name="writing_deltas"
    )
    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.PROTECT, related_name="writing_deltas"
    )
    scene = models.ForeignKey(
        "scenes.Scene", on_delete=models.PROTECT, related_name="writing_deltas"
    )
    revision = models.OneToOneField(
        "scenes.SceneRevision", on_delete=models.PROTECT, related_name="writing_delta"
    )
    activity_date = models.DateField()
    word_delta = models.PositiveIntegerField(default=0)
    resulting_word_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-activity_date", "-created_at")

    def __str__(self) -> str:
        return f"{self.scene}: +{self.word_delta} words"


def _title_errors(value: object) -> dict[str, str]:
    if not isinstance(value, str) or value != value.strip() or not value:
        return {"title": "Title must be present and trimmed."}
    return {}
