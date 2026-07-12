import uuid
from typing import cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from jobs.models import Job
from scenes.models import MutationOperation
from workspaces.models import Workspace


class ImportBatch(models.Model):
    class State(models.TextChoices):
        CREATED = "created", "Created"
        VALIDATING = "validating", "Validating"
        STAGED = "staged", "Staged"
        VALIDATION_FAILED = "validation_failed", "Validation failed"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting approval"
        APPROVED = "approved", "Approved"
        APPLYING = "applying", "Applying"
        APPLIED = "applied", "Applied"
        FAILED_TERMINAL = "failed_terminal", "Failed terminal"
        CANCELLED = "cancelled", "Cancelled"
        QUARANTINED = "quarantined", "Quarantined"

    class Failure(models.TextChoices):
        NONE = "", "None"
        INVALID_SOURCE = "invalid_source", "Invalid source"
        AUTHORIZATION = "authorization", "Authorization"
        CONFLICT = "conflict", "Conflict"
        INTEGRITY = "integrity", "Integrity"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="import_batches"
    )
    source_system = models.CharField(max_length=32, default="legacy_story_engine")
    source_schema_version = models.PositiveSmallIntegerField(default=1)
    source_fingerprint = models.CharField(max_length=64)
    source_size = models.PositiveBigIntegerField()
    transformation_version = models.CharField(max_length=32, default="story-engine-scenes-v1")
    staging_fingerprint = models.CharField(max_length=64, blank=True, default="")
    approved_staging_fingerprint = models.CharField(max_length=64, blank=True, default="")
    state = models.CharField(max_length=24, choices=State.choices, default=State.CREATED)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_import_batches"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_import_batches",
    )
    staging_job = models.ForeignKey(
        Job, on_delete=models.PROTECT, null=True, blank=True, related_name="import_batches"
    )
    accepted_count = models.PositiveIntegerField(default=0)
    transformed_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    failure_classification = models.CharField(
        max_length=24, choices=Failure.choices, blank=True, default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "source_fingerprint", "transformation_version"),
                name="unique_import_source_transformation",
            ),
            models.CheckConstraint(
                condition=Q(source_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="import_source_fingerprint_valid",
            ),
            models.CheckConstraint(
                condition=Q(source_system="legacy_story_engine", source_schema_version=1),
                name="import_source_format_valid",
            ),
            models.CheckConstraint(
                condition=Q(transformation_version="story-engine-scenes-v1"),
                name="import_transformation_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    state__in=(
                        "created",
                        "validating",
                        "staged",
                        "validation_failed",
                        "awaiting_approval",
                        "approved",
                        "applying",
                        "applied",
                        "failed_terminal",
                        "cancelled",
                        "quarantined",
                    )
                ),
                name="import_batch_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    failure_classification__in=(
                        "",
                        "invalid_source",
                        "authorization",
                        "conflict",
                        "integrity",
                    )
                ),
                name="import_batch_failure_valid",
            ),
            models.CheckConstraint(
                condition=Q(staging_fingerprint="")
                | Q(staging_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="import_staging_fingerprint_valid",
            ),
            models.CheckConstraint(
                condition=Q(approved_staging_fingerprint="")
                | Q(approved_staging_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="import_approved_fingerprint_valid",
            ),
        ]
        indexes = [models.Index(fields=("workspace", "state"), name="import_batch_ws_state_idx")]

    def __str__(self) -> str:
        return f"Import Batch {self.id}"


class StagedScene(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        WARNING = "warning", "Warning"
        BLOCKED = "blocked", "Blocked"
        APPLIED = "applied", "Applied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="staged_scenes")
    source_identifier = models.CharField(max_length=128)
    proposed_scene_id = models.UUIDField(default=uuid.uuid4, editable=False)
    proposed_title = models.CharField(max_length=200)
    proposed_lifecycle = models.CharField(max_length=16)
    proposed_ordering = models.PositiveBigIntegerField()
    current_source_revision = models.CharField(max_length=128)
    source_fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "source_identifier"), name="unique_staged_scene_source"
            ),
            models.UniqueConstraint(
                fields=("batch", "proposed_scene_id"), name="unique_staged_scene_target"
            ),
            models.CheckConstraint(
                condition=Q(proposed_lifecycle__in=("active", "archived", "trashed")),
                name="staged_scene_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("accepted", "warning", "blocked", "applied")),
                name="staged_scene_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(source_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="staged_scene_fingerprint_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Staged Scene {self.id}"


class StagedRevision(models.Model):
    class Chronology(models.TextChoices):
        TRUSTED = "trusted", "Trusted"
        UNCERTAIN = "uncertain", "Uncertain"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="staged_revisions"
    )
    staged_scene = models.ForeignKey(
        StagedScene, on_delete=models.CASCADE, related_name="staged_revisions"
    )
    source_identifier = models.CharField(max_length=128)
    proposed_revision_id = models.UUIDField(default=uuid.uuid4, editable=False)
    proposed_revision_number = models.PositiveBigIntegerField()
    content = models.TextField()
    source_content_hash = models.CharField(max_length=64)
    target_content_hash = models.CharField(max_length=64)
    source_timestamp = models.DateTimeField(null=True, blank=True)
    chronology = models.CharField(max_length=16, choices=Chronology.choices)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "staged_scene", "source_identifier"),
                name="unique_staged_revision_source",
            ),
            models.UniqueConstraint(
                fields=("batch", "proposed_revision_id"),
                name="unique_staged_revision_target",
            ),
            models.UniqueConstraint(
                fields=("staged_scene", "proposed_revision_number"),
                name="unique_staged_revision_number",
            ),
            models.UniqueConstraint(
                fields=("staged_scene",),
                condition=Q(is_current=True),
                name="one_current_staged_revision",
            ),
            models.CheckConstraint(
                condition=Q(chronology__in=("trusted", "uncertain")),
                name="staged_revision_chronology_valid",
            ),
            models.CheckConstraint(
                condition=Q(source_content_hash__regex=r"^[0-9a-f]{64}$")
                & Q(target_content_hash__regex=r"^[0-9a-f]{64}$"),
                name="staged_revision_hashes_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Staged Revision {self.id}"


class ImportFinding(models.Model):
    class Severity(models.TextChoices):
        TRANSFORMED = "transformed", "Transformed"
        WARNING = "warning", "Warning"
        DUPLICATE = "duplicate_candidate", "Duplicate candidate"
        CONFLICT = "conflict", "Conflict"
        UNSUPPORTED = "unsupported", "Unsupported"
        REJECTED = "rejected", "Rejected"
        MALFORMED = "malformed", "Malformed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="findings")
    source_entity_type = models.CharField(max_length=32)
    source_identifier = models.CharField(max_length=128, blank=True)
    issue_code = models.CharField(max_length=48)
    severity = models.CharField(max_length=24, choices=Severity.choices)
    field_category = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    severity__in=(
                        "transformed",
                        "warning",
                        "duplicate_candidate",
                        "conflict",
                        "unsupported",
                        "rejected",
                        "malformed",
                    )
                ),
                name="import_finding_severity_valid",
            )
        ]

    def __str__(self) -> str:
        return f"Import Finding {self.id}"


class IdentityMapping(models.Model):
    class EntityType(models.TextChoices):
        SCENE = "scene", "Scene"
        REVISION = "revision", "Revision"

    class State(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPLIED = "applied", "Applied"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="mappings")
    source_system = models.CharField(max_length=32, default="legacy_story_engine")
    source_entity_type = models.CharField(max_length=16, choices=EntityType.choices)
    source_identifier = models.CharField(max_length=128)
    target_entity_type = models.CharField(max_length=16, choices=EntityType.choices)
    target_uuid = models.UUIDField()
    state = models.CharField(max_length=16, choices=State.choices, default=State.PROPOSED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "source_entity_type", "source_identifier"),
                name="unique_import_source_mapping",
            ),
            models.UniqueConstraint(
                fields=("batch", "target_entity_type", "target_uuid"),
                name="unique_import_target_mapping",
            ),
            models.CheckConstraint(
                condition=Q(source_system="legacy_story_engine"),
                name="mapping_source_system_valid",
            ),
            models.CheckConstraint(
                condition=Q(source_entity_type__in=("scene", "revision"))
                & Q(target_entity_type__in=("scene", "revision")),
                name="mapping_entity_types_valid",
            ),
            models.CheckConstraint(
                condition=Q(state__in=("proposed", "applied")), name="mapping_state_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"Identity Mapping {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            prior = (
                IdentityMapping.objects.filter(id=self.id).values_list("state", flat=True).first()
            )
            if prior == self.State.APPLIED:
                raise ValidationError("Applied identity mappings are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        if self.state == self.State.APPLIED:
            raise ValidationError("Applied identity mappings cannot be deleted.")
        return cast(tuple[int, dict[str, int]], super().delete(*args, **kwargs))


class ImportProvenance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="provenance")
    mapping = models.OneToOneField(
        IdentityMapping, on_delete=models.PROTECT, related_name="provenance"
    )
    mutation_operation = models.OneToOneField(
        MutationOperation, on_delete=models.PROTECT, related_name="import_provenance"
    )
    transformation_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Import Provenance {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("Import provenance is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ValidationError("Import provenance cannot be deleted.")
