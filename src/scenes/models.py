import uuid
from typing import cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from scenes.content import CONTENT_FORMAT_VERSION, NORMALIZATION_VERSION
from scenes.exceptions import ImmutableMutationOperationError, ImmutableRevisionError
from scenes.managers import MutationOperationManager, SceneRevisionManager
from workspaces.models import Workspace


class Scene(models.Model):
    class Lifecycle(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        TRASHED = "trashed", "Trashed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="scenes")
    title = models.CharField(max_length=200)
    lifecycle = models.CharField(max_length=16, choices=Lifecycle.choices, default=Lifecycle.ACTIVE)
    ordering = models.BigIntegerField()
    version = models.BigIntegerField(default=0)
    current_revision = models.ForeignKey(
        "SceneRevision",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("ordering", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="scene_title_contains_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(lifecycle__in=("active", "archived", "trashed")),
                name="scene_lifecycle_valid",
            ),
            models.CheckConstraint(condition=Q(ordering__gte=0), name="scene_ordering_nonnegative"),
            models.CheckConstraint(condition=Q(version__gte=0), name="scene_version_nonnegative"),
            models.UniqueConstraint(
                fields=("workspace", "ordering"),
                name="unique_scene_ordering_in_workspace",
            ),
        ]
        indexes = [
            models.Index(
                fields=("workspace", "lifecycle", "ordering"),
                name="scene_ws_lifecycle_order_idx",
            )
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.title, str) or self.title != self.title.strip():
            raise ValidationError({"title": "Scene title must be trimmed."})
        if not self.title:
            raise ValidationError({"title": "Scene title is required."})
        if self.current_revision_id is not None:
            revision = self.current_revision
            if revision.scene_id != self.id or revision.workspace_id != self.workspace_id:
                raise ValidationError(
                    {
                        "current_revision": (
                            "Current Revision must belong to this Scene and Workspace."
                        )
                    }
                )


class MutationOperation(models.Model):
    class OperationType(models.TextChoices):
        SCENE_CREATED = "scene_created", "Scene created"
        SCENE_CONTENT_REVISED = "scene_content_revised", "Scene content revised"

    class Source(models.TextChoices):
        OWNER = "owner", "Owner"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="mutation_operations"
    )
    operation_type = models.CharField(max_length=32, choices=OperationType.choices)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.OWNER)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mutation_operations",
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mutation_operations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = MutationOperationManager()

    class Meta:
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(operation_type__in=("scene_created", "scene_content_revised")),
                name="mutation_operation_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(source__in=("owner",)),
                name="mutation_operation_source_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("workspace", "created_at"),
                name="mutation_ws_created_idx",
            ),
            models.Index(fields=("scene", "created_at"), name="mutation_scene_created_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.get_operation_type_display())

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ImmutableMutationOperationError("Mutation Operations are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ImmutableMutationOperationError("Mutation Operations cannot be deleted.")

    def clean(self) -> None:
        super().clean()
        if self.scene_id is not None and self.scene.workspace_id != self.workspace_id:
            raise ValidationError(
                {"scene": "Mutation Operation Scene must belong to its Workspace."}
            )


class SceneRevision(models.Model):
    class Source(models.TextChoices):
        OWNER = "owner", "Owner"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="scene_revisions"
    )
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="revisions")
    content = models.TextField()
    content_sha256 = models.CharField(max_length=64)
    revision_number = models.PositiveBigIntegerField()
    content_format_version = models.CharField(max_length=32, default=CONTENT_FORMAT_VERSION)
    normalization_version = models.CharField(max_length=32, default=NORMALIZATION_VERSION)
    base_revision = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="derived_revisions",
    )
    restored_from = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="restoration_revisions",
    )
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.OWNER)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="scene_revisions",
    )
    mutation_operation = models.OneToOneField(
        MutationOperation,
        on_delete=models.PROTECT,
        related_name="scene_revision",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SceneRevisionManager()

    class Meta:
        ordering = ("scene_id", "revision_number")
        constraints = [
            models.UniqueConstraint(
                fields=("scene", "revision_number"),
                name="unique_revision_number_in_scene",
            ),
            models.CheckConstraint(
                condition=Q(revision_number__gte=1),
                name="revision_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(content_format_version=CONTENT_FORMAT_VERSION),
                name="revision_content_format_supported",
            ),
            models.CheckConstraint(
                condition=Q(normalization_version=NORMALIZATION_VERSION),
                name="revision_normalization_supported",
            ),
            models.CheckConstraint(
                condition=Q(source__in=("owner",)),
                name="revision_source_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=("scene", "-revision_number"),
                name="revision_scene_num_desc_idx",
            ),
            models.Index(
                fields=("workspace", "created_at"),
                name="revision_ws_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Scene Revision {self.revision_number}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ImmutableRevisionError("Scene Revisions are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ImmutableRevisionError("Scene Revisions cannot be deleted.")

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.scene_id is not None and self.scene.workspace_id != self.workspace_id:
            errors["scene"] = "Revision Scene must belong to its Workspace."
        for field_name in ("base_revision", "restored_from"):
            reference_id = getattr(self, f"{field_name}_id")
            if reference_id is None:
                continue
            reference = getattr(self, field_name)
            if reference.scene_id != self.scene_id or reference.workspace_id != self.workspace_id:
                errors[field_name] = "Lineage must remain in the same Scene and Workspace."
        if self.mutation_operation_id is not None:
            operation = self.mutation_operation
            if operation.workspace_id != self.workspace_id or operation.scene_id != self.scene_id:
                errors["mutation_operation"] = (
                    "Mutation Operation must belong to the same Scene and Workspace."
                )
        if errors:
            raise ValidationError(errors)
