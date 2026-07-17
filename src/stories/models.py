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


def _title_errors(value: object) -> dict[str, str]:
    if not isinstance(value, str) or value != value.strip() or not value:
        return {"title": "Title must be present and trimmed."}
    return {}
