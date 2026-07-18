import uuid

from django.db import models
from django.db.models import Q

from jobs.exceptions import ImmutableJobRecord
from jobs.managers import ProtectedOperationalManager
from workspaces.models import Workspace


class Job(models.Model):
    class JobType(models.TextChoices):
        INTERNAL_NOOP = "internal_noop", "Internal no-op"
        REBUILD_SCENE_SEARCH = "rebuild_scene_search_projection", "Rebuild Scene search"
        VALIDATE_LEGACY_IMPORT = "validate_legacy_import", "Validate legacy import"
        GENERATE_AI_SUGGESTION = "generate_ai_scene_suggestion", "Generate AI Scene suggestion"
        GENERATE_MANUSCRIPT_EXPORT = "generate_manuscript_export", "Generate manuscript export"

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        AVAILABLE = "available", "Available"
        RUNNING = "running", "Running"
        RETRY_WAIT = "retry_wait", "Retry wait"
        CANCELLATION_REQUESTED = "cancellation_requested", "Cancellation requested"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED_TERMINAL = "failed_terminal", "Failed terminal"
        CANCELLED = "cancelled", "Cancelled"
        QUARANTINED = "quarantined", "Quarantined"

    class TargetCategory(models.TextChoices):
        SYSTEM = "system", "System"
        WORKSPACE = "workspace", "Workspace"
        SCENE = "scene", "Scene"
        IMPORT_BATCH = "import_batch", "Import batch"
        AI_REQUEST = "ai_request", "AI request"
        EXPORT = "export", "Export"

    class EffectClass(models.TextChoices):
        INTERNAL_IDEMPOTENT = "internal_idempotent", "Internal idempotent"
        EXTERNAL_AMBIGUOUS = "external_ambiguous", "External ambiguous"

    class Result(models.TextChoices):
        NONE = "", "None"
        SUCCEEDED = "succeeded", "Succeeded"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"
        QUARANTINED = "quarantined", "Quarantined"

    class Failure(models.TextChoices):
        NONE = "", "None"
        TRANSIENT = "transient", "Transient"
        PERMANENT = "permanent", "Permanent"
        AMBIGUOUS = "ambiguous", "Ambiguous"
        LEASE_EXPIRED = "lease_expired", "Lease expired"

    class QuarantineReason(models.TextChoices):
        NONE = "", "None"
        RESTORE = "restore", "Restore"
        AMBIGUOUS_OUTCOME = "ambiguous_outcome", "Ambiguous outcome"
        LEASE_LOSS = "lease_loss", "Lease loss"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, null=True, blank=True, related_name="jobs"
    )
    job_type = models.CharField(max_length=32, choices=JobType.choices)
    state = models.CharField(max_length=24, choices=State.choices)
    target_category = models.CharField(max_length=16, choices=TargetCategory.choices)
    target_id = models.UUIDField(null=True, blank=True)
    expected_revision_id = models.UUIDField(null=True, blank=True)
    expected_scene_version = models.BigIntegerField(null=True, blank=True)
    projection_version = models.CharField(max_length=32, blank=True, default="")
    payload_version = models.PositiveSmallIntegerField(default=1)
    effect_class = models.CharField(max_length=24, choices=EffectClass.choices)
    available_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    lease_id = models.UUIDField(null=True, blank=True)
    lease_owner = models.CharField(max_length=64, blank=True, default="")
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    maximum_attempts = models.PositiveSmallIntegerField(default=3)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    result = models.CharField(max_length=16, choices=Result.choices, blank=True, default="")
    failure = models.CharField(max_length=24, choices=Failure.choices, blank=True, default="")
    quarantine_reason = models.CharField(
        max_length=24, choices=QuarantineReason.choices, blank=True, default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    execution_objects = models.Manager()
    objects = ProtectedOperationalManager()

    class Meta:
        ordering = ("available_at", "created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    state__in=(
                        "queued",
                        "available",
                        "running",
                        "retry_wait",
                        "cancellation_requested",
                        "succeeded",
                        "failed_terminal",
                        "cancelled",
                        "quarantined",
                    )
                ),
                name="job_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    job_type__in=(
                        "internal_noop",
                        "rebuild_scene_search_projection",
                        "validate_legacy_import",
                        "generate_ai_scene_suggestion",
                        "generate_manuscript_export",
                    )
                ),
                name="job_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    target_category__in=(
                        "system",
                        "workspace",
                        "scene",
                        "import_batch",
                        "ai_request",
                        "export",
                    )
                ),
                name="job_target_category_valid",
            ),
            models.CheckConstraint(
                condition=Q(effect_class__in=("internal_idempotent", "external_ambiguous")),
                name="job_effect_class_valid",
            ),
            models.CheckConstraint(
                condition=Q(result__in=("", "succeeded", "cancelled", "failed", "quarantined")),
                name="job_result_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    failure__in=("", "transient", "permanent", "ambiguous", "lease_expired")
                ),
                name="job_failure_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    quarantine_reason__in=("", "restore", "ambiguous_outcome", "lease_loss")
                ),
                name="job_quarantine_reason_valid",
            ),
            models.CheckConstraint(
                condition=Q(payload_version=1), name="job_payload_version_valid"
            ),
            models.CheckConstraint(
                condition=Q(expected_scene_version__isnull=True) | Q(expected_scene_version__gte=1),
                name="job_expected_scene_version_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        job_type="internal_noop",
                        expected_revision_id__isnull=True,
                        expected_scene_version__isnull=True,
                        projection_version="",
                    )
                    | Q(
                        job_type="rebuild_scene_search_projection",
                        workspace__isnull=False,
                        target_category="scene",
                        target_id__isnull=False,
                        expected_revision_id__isnull=False,
                        expected_scene_version__isnull=False,
                        projection_version="scene-search-v1:simple-v1",
                    )
                    | Q(
                        job_type="validate_legacy_import",
                        workspace__isnull=False,
                        target_category="import_batch",
                        target_id__isnull=False,
                        expected_revision_id__isnull=True,
                        expected_scene_version__isnull=True,
                        projection_version="story-engine-scenes-v1",
                    )
                    | Q(
                        job_type="generate_ai_scene_suggestion",
                        workspace__isnull=False,
                        target_category="ai_request",
                        target_id__isnull=False,
                        expected_revision_id__isnull=False,
                        expected_scene_version__isnull=False,
                        projection_version="ai-scene-v1",
                        effect_class="external_ambiguous",
                    )
                    | Q(
                        job_type="generate_manuscript_export",
                        workspace__isnull=False,
                        target_category="export",
                        target_id__isnull=False,
                        expected_revision_id__isnull=True,
                        expected_scene_version__isnull=True,
                        projection_version="publishing-export-v1",
                        effect_class="internal_idempotent",
                    )
                ),
                name="job_type_parameters_consistent",
            ),
            models.CheckConstraint(
                condition=Q(maximum_attempts__gte=1), name="job_max_attempts_valid"
            ),
            models.CheckConstraint(
                condition=Q(attempt_count__lte=models.F("maximum_attempts")),
                name="job_attempt_count_bounded",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        state__in=("running", "cancellation_requested"),
                        lease_id__isnull=False,
                        lease_owner__regex=r"^[A-Za-z0-9._~-]{1,64}$",
                        lease_expires_at__isnull=False,
                    )
                    | Q(
                        state__in=(
                            "queued",
                            "available",
                            "retry_wait",
                            "succeeded",
                            "failed_terminal",
                            "cancelled",
                            "quarantined",
                        ),
                        lease_id__isnull=True,
                        lease_owner="",
                        lease_expires_at__isnull=True,
                    )
                ),
                name="job_lease_state_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=("state", "available_at", "created_at"), name="job_claim_idx"),
            models.Index(fields=("state", "lease_expires_at"), name="job_lease_recovery_idx"),
            models.Index(fields=("workspace", "state"), name="job_workspace_state_idx"),
        ]

    def __str__(self) -> str:
        return f"Job {self.id}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ImmutableJobRecord("Jobs require the state-machine service.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ImmutableJobRecord("Jobs cannot be deleted.")


class JobAttempt(models.Model):
    class Outcome(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        RETRYABLE = "retryable", "Retryable"
        TERMINAL = "terminal", "Terminal"
        CANCELLED = "cancelled", "Cancelled"
        AMBIGUOUS = "ambiguous", "Ambiguous"
        LEASE_LOST = "lease_lost", "Lease lost"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="attempts")
    attempt_number = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    worker_id = models.CharField(max_length=64)
    lease_id = models.UUIDField()
    outcome = models.CharField(max_length=16, choices=Outcome.choices, default=Outcome.RUNNING)
    error_category = models.CharField(
        max_length=24, choices=Job.Failure.choices, blank=True, default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)

    execution_objects = models.Manager()
    objects = ProtectedOperationalManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("job", "attempt_number"), name="unique_job_attempt_number"
            ),
            models.CheckConstraint(
                condition=Q(
                    outcome__in=(
                        "running",
                        "succeeded",
                        "retryable",
                        "terminal",
                        "cancelled",
                        "ambiguous",
                        "lease_lost",
                        "quarantined",
                    )
                ),
                name="job_attempt_outcome_valid",
            ),
            models.CheckConstraint(
                condition=Q(worker_id__regex=r"^[A-Za-z0-9._~-]{1,64}$"),
                name="job_attempt_worker_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    error_category__in=(
                        "",
                        "transient",
                        "permanent",
                        "ambiguous",
                        "lease_expired",
                    )
                ),
                name="job_attempt_error_valid",
            ),
        ]
        indexes = [models.Index(fields=("job", "attempt_number"), name="job_attempt_lookup_idx")]

    def __str__(self) -> str:
        return f"Job Attempt {self.attempt_number}"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ImmutableJobRecord("Job Attempts require the execution service.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ImmutableJobRecord("Job Attempts cannot be deleted.")


class IdempotencyRecord(models.Model):
    class Caller(models.TextChoices):
        WEB = "web", "Web"
        OPERATOR = "operator", "Operator"
        SERVICE = "service", "Service"

    class Operation(models.TextChoices):
        ENQUEUE_JOB = "enqueue_job", "Enqueue job"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED_TERMINAL = "failed_terminal", "Failed terminal"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="idempotency_records",
    )
    caller = models.CharField(max_length=16, choices=Caller.choices)
    caller_reference = models.CharField(max_length=64)
    operation = models.CharField(max_length=32, choices=Operation.choices)
    idempotency_key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    state = models.CharField(max_length=24, choices=State.choices, default=State.PENDING)
    resulting_job = models.ForeignKey(
        Job, on_delete=models.PROTECT, null=True, blank=True, related_name="idempotency_records"
    )
    result_classification = models.CharField(max_length=24, blank=True, default="")
    failure_classification = models.CharField(max_length=24, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    execution_objects = models.Manager()
    objects = ProtectedOperationalManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "caller", "caller_reference", "operation", "idempotency_key"),
                name="unique_generic_idempotency_scope",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=Q(idempotency_key__regex=r"^[A-Za-z0-9._~-]{16,128}$"),
                name="generic_idempotency_key_valid",
            ),
            models.CheckConstraint(
                condition=Q(request_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="generic_idempotency_fingerprint_valid",
            ),
            models.CheckConstraint(
                condition=Q(caller_reference__regex=r"^[A-Za-z0-9._~-]{1,64}$"),
                name="generic_idempotency_caller_valid",
            ),
            models.CheckConstraint(
                condition=Q(caller__in=("web", "operator", "service")),
                name="generic_idempotency_caller_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(operation__in=("enqueue_job",)),
                name="generic_idempotency_operation_valid",
            ),
            models.CheckConstraint(
                condition=Q(state__in=("pending", "succeeded", "failed_terminal")),
                name="generic_idempotency_state_valid",
            ),
            models.CheckConstraint(
                condition=Q(result_classification__in=("", "job_enqueued")),
                name="generic_idempotency_result_valid",
            ),
            models.CheckConstraint(
                condition=Q(failure_classification__in=("", "invalid_request")),
                name="generic_idempotency_failure_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        state="pending",
                        resulting_job__isnull=True,
                        result_classification="",
                        failure_classification="",
                        completed_at__isnull=True,
                    )
                    | Q(
                        state="succeeded",
                        resulting_job__isnull=False,
                        result_classification="job_enqueued",
                        failure_classification="",
                        completed_at__isnull=False,
                    )
                    | Q(
                        state="failed_terminal",
                        resulting_job__isnull=True,
                        result_classification="",
                        failure_classification="invalid_request",
                        completed_at__isnull=False,
                    )
                ),
                name="generic_idempotency_outcome_consistent",
            ),
        ]
        indexes = [
            models.Index(
                fields=("workspace", "operation", "created_at"), name="idempotency_lookup_idx"
            )
        ]

    def __str__(self) -> str:
        return "Idempotency Record"

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ImmutableJobRecord("Idempotency Records require the enqueue service.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ImmutableJobRecord("Idempotency Records cannot be deleted.")
