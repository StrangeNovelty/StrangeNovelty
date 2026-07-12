import random
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from jobs.exceptions import (
    AmbiguousJobOutcome,
    IdempotencyConflict,
    InvalidJobTransition,
    RetryableJobError,
    StaleJobLease,
    TerminalJobError,
)
from jobs.models import IdempotencyRecord, Job, JobAttempt
from jobs.registry import HandlerOutcome, JobContext, get_handler
from workspaces.models import Workspace

KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")
REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{1,64}$")
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_LEASE_SECONDS = 60
DEFAULT_MAXIMUM_ATTEMPTS = 3
MAXIMUM_RETRY_DELAY_SECONDS = 300


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    job: Job
    idempotency_record: IdempotencyRecord
    replayed: bool


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    job: Job
    attempt: JobAttempt
    lease_id: uuid.UUID


def enqueue_job(
    *,
    workspace: Workspace | None,
    caller: str,
    caller_reference: str,
    idempotency_key: str,
    request_fingerprint: str,
    job_type: str = "internal_noop",
    target_category: str = "system",
    target_id: uuid.UUID | None = None,
    expected_revision_id: uuid.UUID | None = None,
    expected_scene_version: int | None = None,
    projection_version: str = "",
    effect_class: str = "internal_idempotent",
    available_at: datetime | None = None,
    maximum_attempts: int = DEFAULT_MAXIMUM_ATTEMPTS,
) -> EnqueueResult:
    get_handler(job_type)
    if target_category not in ("system", "workspace", "scene", "import_batch"):
        raise ValueError("Invalid target category.")
    if effect_class not in ("internal_idempotent", "external_ambiguous"):
        raise ValueError("Invalid effect classification.")
    if caller not in ("web", "operator", "service"):
        raise ValueError("Invalid caller classification.")
    if not REFERENCE_PATTERN.fullmatch(caller_reference):
        raise ValueError("Invalid caller reference.")
    if not KEY_PATTERN.fullmatch(idempotency_key):
        raise ValueError("Invalid idempotency key.")
    if not FINGERPRINT_PATTERN.fullmatch(request_fingerprint):
        raise ValueError("Invalid request fingerprint.")
    if maximum_attempts < 1 or maximum_attempts > 20:
        raise ValueError("Invalid maximum attempts.")
    now = timezone.now()
    ready_at = available_at if available_at is not None else now

    with transaction.atomic():
        record = _reserve_idempotency(
            workspace=workspace,
            caller=caller,
            caller_reference=caller_reference,
            idempotency_key=idempotency_key,
            fingerprint=request_fingerprint,
        )
        if record.request_fingerprint != request_fingerprint:
            raise IdempotencyConflict("Idempotency key fingerprint differs.")
        if record.state == IdempotencyRecord.State.SUCCEEDED:
            if record.resulting_job is None:
                raise InvalidJobTransition("Completed idempotency record has no Job.")
            return EnqueueResult(record.resulting_job, record, True)

        state = "available" if ready_at <= now else "queued"
        job = Job.execution_objects.create(
            workspace=workspace,
            job_type=job_type,
            state=state,
            target_category=target_category,
            target_id=target_id,
            expected_revision_id=expected_revision_id,
            expected_scene_version=expected_scene_version,
            projection_version=projection_version,
            payload_version=1,
            effect_class=effect_class,
            available_at=ready_at,
            maximum_attempts=maximum_attempts,
        )
        completed_at = timezone.now()
        IdempotencyRecord.execution_objects.filter(id=record.id).update(
            state=IdempotencyRecord.State.SUCCEEDED,
            resulting_job=job,
            result_classification="job_enqueued",
            completed_at=completed_at,
        )
        record = cast(IdempotencyRecord, IdempotencyRecord.execution_objects.get(id=record.id))
        return EnqueueResult(cast(Job, job), record, False)


def _reserve_idempotency(
    *,
    workspace: Workspace | None,
    caller: str,
    caller_reference: str,
    idempotency_key: str,
    fingerprint: str,
) -> IdempotencyRecord:
    lookup = {
        "workspace": workspace,
        "caller": caller,
        "caller_reference": caller_reference,
        "operation": IdempotencyRecord.Operation.ENQUEUE_JOB,
        "idempotency_key": idempotency_key,
    }
    try:
        return cast(
            IdempotencyRecord,
            IdempotencyRecord.execution_objects.select_for_update().get(**lookup),
        )
    except IdempotencyRecord.DoesNotExist:
        try:
            with transaction.atomic():
                IdempotencyRecord.execution_objects.create(
                    request_fingerprint=fingerprint, **lookup
                )
        except IntegrityError:
            pass
        return cast(
            IdempotencyRecord,
            IdempotencyRecord.execution_objects.select_for_update().get(**lookup),
        )


def claim_jobs(
    *,
    worker_id: str,
    batch_size: int = 1,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    now: datetime | None = None,
) -> list[ClaimedJob]:
    if not REFERENCE_PATTERN.fullmatch(worker_id):
        raise ValueError("Invalid worker identifier.")
    if batch_size < 1 or batch_size > 100 or lease_seconds < 1 or lease_seconds > 3600:
        raise ValueError("Invalid claim bounds.")
    claimed_at = now if now is not None else timezone.now()
    results: list[ClaimedJob] = []
    with transaction.atomic():
        jobs = list(
            Job.execution_objects.select_for_update(skip_locked=True)
            .filter(
                state__in=(Job.State.QUEUED, Job.State.AVAILABLE, Job.State.RETRY_WAIT),
                available_at__lte=claimed_at,
                attempt_count__lt=F("maximum_attempts"),
            )
            .order_by("available_at", "created_at", "id")[:batch_size]
        )
        for job in jobs:
            lease_id = uuid.uuid4()
            attempt_number = job.attempt_count + 1
            expires_at = claimed_at + timedelta(seconds=lease_seconds)
            Job.execution_objects.filter(id=job.id).update(
                state=Job.State.RUNNING,
                started_at=job.started_at or claimed_at,
                lease_id=lease_id,
                lease_owner=worker_id,
                lease_expires_at=expires_at,
                heartbeat_at=claimed_at,
                attempt_count=attempt_number,
                updated_at=claimed_at,
            )
            attempt = JobAttempt.execution_objects.create(
                job=job,
                attempt_number=attempt_number,
                started_at=claimed_at,
                worker_id=worker_id,
                lease_id=lease_id,
                outcome=JobAttempt.Outcome.RUNNING,
            )
            job = cast(Job, Job.execution_objects.get(id=job.id))
            results.append(ClaimedJob(job, cast(JobAttempt, attempt), lease_id))
    return results


def heartbeat_job(
    *, claimed: ClaimedJob, lease_seconds: int = DEFAULT_LEASE_SECONDS, now: datetime | None = None
) -> None:
    moment = now if now is not None else timezone.now()
    with transaction.atomic():
        job = _locked_lease(claimed.job.id, claimed.lease_id)
        if job.lease_expires_at is None or job.lease_expires_at <= moment:
            raise StaleJobLease("Job lease expired.")
        Job.execution_objects.filter(id=job.id).update(
            heartbeat_at=moment,
            lease_expires_at=moment + timedelta(seconds=lease_seconds),
            updated_at=moment,
        )


def execute_claim(claimed: ClaimedJob, *, rng: random.Random | None = None) -> Job:
    job = cast(Job, Job.execution_objects.get(id=claimed.job.id))
    if job.workspace_id is not None:
        workspace = cast(Workspace, Workspace.objects.filter(id=job.workspace_id).first())
        if workspace is None or not workspace.is_active:
            return _finalize(claimed, "terminal", Job.Failure.PERMANENT, rng=rng)
    if _cancellation_requested(job.id):
        return _finalize(claimed, "cancelled", Job.Failure.NONE, rng=rng)

    context = JobContext(
        job_id=str(job.id),
        workspace_id=str(job.workspace_id) if job.workspace_id else None,
        cancellation_requested=lambda: _cancellation_requested(job.id),
    )
    try:
        result = get_handler(job.job_type)(context)
        outcome = "success" if result.outcome == HandlerOutcome.SUCCEEDED else "terminal"
        return _finalize(claimed, outcome, Job.Failure.NONE, rng=rng)
    except RetryableJobError:
        return _finalize(claimed, "retryable", Job.Failure.TRANSIENT, rng=rng)
    except TerminalJobError:
        return _finalize(claimed, "terminal", Job.Failure.PERMANENT, rng=rng)
    except AmbiguousJobOutcome:
        return _finalize(claimed, "ambiguous", Job.Failure.AMBIGUOUS, rng=rng)
    except Exception:
        return _finalize(claimed, "terminal", Job.Failure.PERMANENT, rng=rng)


def _finalize(
    claimed: ClaimedJob,
    outcome: str,
    error_category: Any,
    *,
    rng: random.Random | None,
) -> Job:
    moment = timezone.now()
    with transaction.atomic():
        job = _locked_lease(claimed.job.id, claimed.lease_id)
        attempt = cast(
            JobAttempt,
            JobAttempt.execution_objects.select_for_update().get(id=claimed.attempt.id),
        )
        if attempt.finished_at is not None:
            raise StaleJobLease("Job Attempt already finished.")
        state: Any
        result: Any = ""
        quarantine: Any = ""
        available_at = job.available_at
        attempt_outcome: Any
        if job.state == Job.State.CANCELLATION_REQUESTED or outcome == "cancelled":
            state, result, attempt_outcome = (
                Job.State.CANCELLED,
                Job.Result.CANCELLED,
                JobAttempt.Outcome.CANCELLED,
            )
        elif outcome == "success":
            state, result, attempt_outcome = (
                Job.State.SUCCEEDED,
                Job.Result.SUCCEEDED,
                JobAttempt.Outcome.SUCCEEDED,
            )
        elif outcome == "ambiguous":
            state, result, quarantine, attempt_outcome = (
                Job.State.QUARANTINED,
                Job.Result.QUARANTINED,
                Job.QuarantineReason.AMBIGUOUS_OUTCOME,
                JobAttempt.Outcome.AMBIGUOUS,
            )
        elif outcome == "retryable" and job.attempt_count < job.maximum_attempts:
            state, attempt_outcome = Job.State.RETRY_WAIT, JobAttempt.Outcome.RETRYABLE
            available_at = moment + retry_delay(job.attempt_count, rng=rng)
        else:
            state, result, attempt_outcome = (
                Job.State.FAILED_TERMINAL,
                Job.Result.FAILED,
                JobAttempt.Outcome.TERMINAL,
            )
        terminal = state in (
            Job.State.SUCCEEDED,
            Job.State.FAILED_TERMINAL,
            Job.State.CANCELLED,
            Job.State.QUARANTINED,
        )
        Job.execution_objects.filter(id=job.id).update(
            state=state,
            result=result,
            failure=error_category,
            quarantine_reason=quarantine,
            available_at=available_at,
            finished_at=moment if terminal else None,
            lease_id=None,
            lease_owner="",
            lease_expires_at=None,
            heartbeat_at=None,
            updated_at=moment,
        )
        JobAttempt.execution_objects.filter(id=attempt.id).update(
            finished_at=moment,
            outcome=attempt_outcome,
            error_category=error_category,
        )
        return cast(Job, Job.execution_objects.get(id=job.id))


def _locked_lease(job_id: uuid.UUID, lease_id: uuid.UUID) -> Job:
    try:
        return cast(
            Job,
            Job.execution_objects.select_for_update().get(
                id=job_id,
                lease_id=lease_id,
                state__in=(Job.State.RUNNING, Job.State.CANCELLATION_REQUESTED),
            ),
        )
    except Job.DoesNotExist as exc:
        raise StaleJobLease("Job lease is no longer owned.") from exc


def _cancellation_requested(job_id: uuid.UUID) -> bool:
    return cast(
        bool,
        Job.execution_objects.filter(id=job_id, state=Job.State.CANCELLATION_REQUESTED).exists(),
    )


def retry_delay(attempt_count: int, *, rng: random.Random | None = None) -> timedelta:
    generator = rng or random.SystemRandom()
    base = min(MAXIMUM_RETRY_DELAY_SECONDS, 5 * (2 ** max(0, attempt_count - 1)))
    return timedelta(
        seconds=min(MAXIMUM_RETRY_DELAY_SECONDS, base + generator.uniform(0, base / 4))
    )


def request_cancellation(job_id: uuid.UUID) -> Job:
    moment = timezone.now()
    with transaction.atomic():
        job = cast(Job, Job.execution_objects.select_for_update().get(id=job_id))
        if job.state in (Job.State.QUEUED, Job.State.AVAILABLE, Job.State.RETRY_WAIT):
            Job.execution_objects.filter(id=job.id).update(
                state=Job.State.CANCELLED,
                result=Job.Result.CANCELLED,
                cancellation_requested_at=moment,
                finished_at=moment,
                updated_at=moment,
            )
        elif job.state == Job.State.RUNNING:
            Job.execution_objects.filter(id=job.id).update(
                state=Job.State.CANCELLATION_REQUESTED,
                cancellation_requested_at=moment,
                updated_at=moment,
            )
        elif job.state == Job.State.CANCELLATION_REQUESTED:
            pass
        else:
            raise InvalidJobTransition("Terminal Jobs cannot be cancelled or reopened.")
        return cast(Job, Job.execution_objects.get(id=job.id))


def recover_expired_leases(*, now: datetime | None = None) -> int:
    moment = now if now is not None else timezone.now()
    recovered = 0
    with transaction.atomic():
        jobs = list(
            Job.execution_objects.select_for_update(skip_locked=True).filter(
                state__in=(Job.State.RUNNING, Job.State.CANCELLATION_REQUESTED),
                lease_expires_at__lt=moment,
            )
        )
        for job in jobs:
            state: Any
            result: Any
            quarantine: Any
            attempt = JobAttempt.execution_objects.filter(
                job=job, attempt_number=job.attempt_count, finished_at__isnull=True
            ).first()
            if attempt is not None:
                JobAttempt.execution_objects.filter(id=attempt.id).update(
                    finished_at=moment,
                    outcome=JobAttempt.Outcome.LEASE_LOST,
                    error_category=Job.Failure.LEASE_EXPIRED,
                )
            if job.state == Job.State.CANCELLATION_REQUESTED:
                state, result, quarantine = Job.State.CANCELLED, Job.Result.CANCELLED, ""
            elif job.effect_class == Job.EffectClass.EXTERNAL_AMBIGUOUS:
                state, result, quarantine = (
                    Job.State.QUARANTINED,
                    Job.Result.QUARANTINED,
                    Job.QuarantineReason.LEASE_LOSS,
                )
            elif job.attempt_count >= job.maximum_attempts:
                state, result, quarantine = (
                    Job.State.FAILED_TERMINAL,
                    Job.Result.FAILED,
                    "",
                )
            else:
                state, result, quarantine = Job.State.RETRY_WAIT, "", ""
            terminal = state != Job.State.RETRY_WAIT
            Job.execution_objects.filter(id=job.id).update(
                state=state,
                result=result,
                failure=Job.Failure.LEASE_EXPIRED,
                quarantine_reason=quarantine,
                available_at=moment,
                finished_at=moment if terminal else None,
                lease_id=None,
                lease_owner="",
                lease_expires_at=None,
                heartbeat_at=None,
                updated_at=moment,
            )
            recovered += 1
    return recovered


def quarantine_unfinished_jobs() -> int:
    moment = timezone.now()
    unfinished = (
        Job.State.QUEUED,
        Job.State.AVAILABLE,
        Job.State.RUNNING,
        Job.State.RETRY_WAIT,
        Job.State.CANCELLATION_REQUESTED,
    )
    with transaction.atomic():
        jobs = list(Job.execution_objects.select_for_update().filter(state__in=unfinished))
        for job in jobs:
            JobAttempt.execution_objects.filter(job=job, finished_at__isnull=True).update(
                finished_at=moment,
                outcome=JobAttempt.Outcome.QUARANTINED,
                error_category=Job.Failure.AMBIGUOUS,
            )
            Job.execution_objects.filter(id=job.id).update(
                state=Job.State.QUARANTINED,
                result=Job.Result.QUARANTINED,
                quarantine_reason=Job.QuarantineReason.RESTORE,
                finished_at=moment,
                lease_id=None,
                lease_owner="",
                lease_expires_at=None,
                heartbeat_at=None,
                updated_at=moment,
            )
    return len(jobs)
