import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from jobs.models import Job, JobAttempt
from scenes.models import MutationOperation, Scene, SceneRevision
from workspaces.models import Workspace


class AIRequest(models.Model):
    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="ai_requests")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ai_requests"
    )
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="ai_requests")
    source_revision = models.ForeignKey(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_requests"
    )
    source_scene_version = models.PositiveBigIntegerField()
    source_content_hash = models.CharField(max_length=64)
    capability = models.CharField(max_length=32, default="scene_revision_suggestion")
    prompt_template = models.CharField(max_length=32, default="scene-review")
    prompt_template_version = models.CharField(max_length=16, default="v1")
    configuration_version = models.CharField(max_length=32, default="ai-scene-v1")
    instruction = models.TextField(max_length=1000)
    instruction_hash = models.CharField(max_length=64)
    provider = models.CharField(max_length=32, default="local_fake")
    requested_model = models.CharField(max_length=32, default="deterministic-v1")
    request_fingerprint = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=128)
    state = models.CharField(max_length=16, choices=State.choices, default=State.QUEUED)
    job = models.OneToOneField(
        Job, on_delete=models.PROTECT, null=True, blank=True, related_name="ai_request"
    )
    maximum_output_characters = models.PositiveIntegerField(default=1_000_000)
    failure_classification = models.CharField(max_length=24, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "requested_by", "idempotency_key"),
                name="unique_ai_request_key",
            ),
            models.CheckConstraint(
                condition=Q(source_content_hash__regex=r"^[0-9a-f]{64}$")
                & Q(instruction_hash__regex=r"^[0-9a-f]{64}$")
                & Q(request_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="ai_request_hashes_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    capability="scene_revision_suggestion",
                    prompt_template="scene-review",
                    prompt_template_version="v1",
                    configuration_version="ai-scene-v1",
                ),
                name="ai_request_versions_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    state__in=(
                        "queued",
                        "running",
                        "completed",
                        "failed",
                        "cancelled",
                        "expired",
                        "quarantined",
                    )
                ),
                name="ai_request_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(idempotency_key__regex=r"^[A-Za-z0-9._~-]{16,128}$"),
                name="ai_request_key_valid",
            ),
        ]
        indexes = [models.Index(fields=("workspace", "state"), name="ai_request_ws_state_idx")]

    def __str__(self) -> str:
        return f"AI Request {self.id}"


class AIContextManifest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(
        AIRequest, on_delete=models.PROTECT, related_name="context_manifest"
    )
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_context_manifests"
    )
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="ai_context_manifests")
    source_revision = models.ForeignKey(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_context_manifests"
    )
    source_scene_version = models.PositiveBigIntegerField()
    source_content_hash = models.CharField(max_length=64)
    capability = models.CharField(max_length=32)
    prompt_template = models.CharField(max_length=32)
    prompt_template_version = models.CharField(max_length=16)
    configuration_version = models.CharField(max_length=32)
    context_construction_version = models.CharField(max_length=32, default="single-scene-v1")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"AI Context Manifest {self.id}"


class ProviderEffect(models.Model):
    class Outcome(models.TextChoices):
        INTENDED = "intended", "Intended"
        KNOWN_SUCCESS = "known_success", "Known success"
        KNOWN_FAILURE = "known_failure", "Known failure"
        AMBIGUOUS = "ambiguous", "Ambiguous"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(
        AIRequest, on_delete=models.PROTECT, related_name="provider_effects"
    )
    job_attempt = models.ForeignKey(
        JobAttempt, on_delete=models.PROTECT, null=True, blank=True, related_name="provider_effects"
    )
    provider = models.CharField(max_length=32)
    operation_identifier = models.CharField(max_length=64, blank=True, default="")
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    ambiguity_classification = models.CharField(max_length=24, blank=True, default="")
    requested_at = models.DateTimeField()
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("request", "job_attempt"),
                condition=Q(job_attempt__isnull=False),
                name="unique_ai_effect_attempt",
            ),
            models.CheckConstraint(
                condition=Q(
                    outcome__in=(
                        "intended",
                        "known_success",
                        "known_failure",
                        "ambiguous",
                        "cancelled",
                    )
                ),
                name="provider_effect_outcome_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Provider Effect {self.id}"


class AISuggestion(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        REJECTED = "rejected", "Rejected"
        APPLIED = "applied", "Applied"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ai_suggestions"
    )
    request = models.OneToOneField(AIRequest, on_delete=models.PROTECT, related_name="suggestion")
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="ai_suggestions")
    source_revision = models.ForeignKey(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_suggestions"
    )
    source_scene_version = models.PositiveBigIntegerField()
    source_content_hash = models.CharField(max_length=64)
    original_output = models.TextField(max_length=1_000_000)
    review_text = models.TextField(max_length=1_000_000)
    output_hash = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    provider = models.CharField(max_length=32)
    model_classification = models.CharField(max_length=32)
    prompt_template = models.CharField(max_length=32)
    prompt_template_version = models.CharField(max_length=16)
    provider_operation_identifier = models.CharField(max_length=64, blank=True, default="")
    input_units = models.PositiveIntegerField(default=0)
    output_units = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    quarantined_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_ai_suggestions",
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applied_ai_suggestions",
    )
    resulting_revision = models.ForeignKey(
        SceneRevision,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="applied_ai_suggestions",
    )
    resulting_scene_version = models.PositiveBigIntegerField(null=True, blank=True)
    disposition_classification = models.CharField(max_length=24, blank=True, default="")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    state__in=(
                        "pending",
                        "ready",
                        "rejected",
                        "applied",
                        "expired",
                        "failed",
                        "quarantined",
                    )
                ),
                name="ai_suggestion_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(source_content_hash__regex=r"^[0-9a-f]{64}$")
                & Q(output_hash__regex=r"^[0-9a-f]{64}$"),
                name="ai_suggestion_hashes_valid",
            ),
        ]
        indexes = [models.Index(fields=("workspace", "state"), name="ai_suggestion_ws_state_idx")]

    def __str__(self) -> str:
        return f"AI Suggestion {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            original = (
                AISuggestion.objects.filter(id=self.id)
                .values_list("original_output", flat=True)
                .first()
            )
            if original != self.original_output:
                raise ValidationError("Original AI output is immutable.")
        super().save(*args, **kwargs)


class AISuggestionApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suggestion = models.OneToOneField(
        AISuggestion, on_delete=models.PROTECT, related_name="application_provenance"
    )
    revision = models.OneToOneField(
        SceneRevision, on_delete=models.PROTECT, related_name="ai_application_provenance"
    )
    mutation_operation = models.OneToOneField(
        MutationOperation, on_delete=models.PROTECT, related_name="ai_application_provenance"
    )
    applied_text_hash = models.CharField(max_length=64)
    human_edited = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"AI Suggestion Application {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ValidationError("AI application provenance is append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ValidationError("AI application provenance cannot be deleted.")
