import os
import random
import uuid
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db import transaction
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
from jobs.registry import HandlerOutcome, HandlerResult
from jobs.services import (
    EnqueueResult,
    claim_jobs,
    enqueue_job,
    execute_claim,
    heartbeat_job,
    quarantine_unfinished_jobs,
    recover_expired_leases,
    request_cancellation,
)
from workspaces.models import Workspace

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

FINGERPRINT = "a" * 64


def _enqueue(
    *,
    workspace: Workspace | None = None,
    key: str | None = None,
    fingerprint: str = FINGERPRINT,
    available_at: datetime | None = None,
    maximum_attempts: int = 3,
    effect_class: str = "internal_idempotent",
) -> EnqueueResult:
    return enqueue_job(
        workspace=workspace,
        caller="service",
        caller_reference="phase6-tests",
        idempotency_key=key or uuid.uuid4().hex,
        request_fingerprint=fingerprint,
        available_at=available_at,
        maximum_attempts=maximum_attempts,
        effect_class=effect_class,
    )


def test_enqueue_is_commit_coupled_and_does_not_execute() -> None:
    with pytest.raises(RuntimeError), transaction.atomic():
        _enqueue()
        assert Job.objects.count() == 1
        raise RuntimeError("rollback")
    assert Job.objects.count() == 0
    assert IdempotencyRecord.objects.count() == 0

    result = _enqueue()
    assert result.job.state == Job.State.AVAILABLE
    assert result.job.attempt_count == 0
    assert JobAttempt.objects.count() == 0


def test_idempotent_enqueue_converges_and_conflicting_fingerprint_fails() -> None:
    key = uuid.uuid4().hex
    first = _enqueue(key=key)
    replay = _enqueue(key=key)
    assert replay.replayed
    assert replay.job.id == first.job.id
    assert Job.objects.count() == 1
    with pytest.raises(IdempotencyConflict):
        _enqueue(key=key, fingerprint="b" * 64)


def test_workspace_scope_is_preserved() -> None:
    workspace = Workspace.objects.create(name="Synthetic Job Workspace")
    result = _enqueue(workspace=workspace)
    assert result.job.workspace == workspace


def test_claiming_obeys_schedule_order_and_excludes_terminal() -> None:
    now = timezone.now()
    first = _enqueue(available_at=now - timedelta(seconds=2)).job
    second = _enqueue(available_at=now - timedelta(seconds=1)).job
    future = _enqueue(available_at=now + timedelta(hours=1)).job
    Job.execution_objects.filter(id=second.id).update(
        state=Job.State.QUARANTINED,
        result=Job.Result.QUARANTINED,
        quarantine_reason=Job.QuarantineReason.RESTORE,
        finished_at=now,
    )
    claimed = claim_jobs(worker_id="worker-one", batch_size=5, now=now)
    assert [item.job.id for item in claimed] == [first.id]
    assert future.id not in [item.job.id for item in claimed]
    assert claimed[0].job.attempt_count == 1
    assert claimed[0].attempt.attempt_number == 1
    assert claimed[0].job.lease_id == claimed[0].lease_id


def test_two_workers_cannot_claim_the_same_job() -> None:
    job = _enqueue().job
    first = claim_jobs(worker_id="worker-one")
    second = claim_jobs(worker_id="worker-two")
    assert len(first) == 1
    assert second == []
    assert first[0].job.id == job.id
    assert JobAttempt.objects.filter(job=job).count() == 1


def test_heartbeat_and_stale_lease_finalization() -> None:
    claimed = claim_jobs(worker_id="worker-one")[0] if Job.objects.exists() else None
    if claimed is None:
        _enqueue()
        claimed = claim_jobs(worker_id="worker-one")[0]
    original_expiry = claimed.job.lease_expires_at
    heartbeat_job(claimed=claimed, lease_seconds=120)
    claimed.job.refresh_from_db()
    assert claimed.job.lease_expires_at > original_expiry
    Job.execution_objects.filter(id=claimed.job.id).update(lease_id=uuid.uuid4())
    with pytest.raises(StaleJobLease):
        execute_claim(claimed)


def test_success_retry_terminal_and_ambiguous_finalization() -> None:
    scenarios = (
        (lambda _context: HandlerResult(HandlerOutcome.SUCCEEDED), Job.State.SUCCEEDED),
        (lambda _context: (_ for _ in ()).throw(RetryableJobError()), Job.State.RETRY_WAIT),
        (lambda _context: (_ for _ in ()).throw(TerminalJobError()), Job.State.FAILED_TERMINAL),
        (lambda _context: (_ for _ in ()).throw(AmbiguousJobOutcome()), Job.State.QUARANTINED),
    )
    for handler, expected_state in scenarios:
        claimed = (
            claim_jobs(worker_id=f"worker-{uuid.uuid4().hex[:8]}")[0]
            if Job.objects.filter(state=Job.State.AVAILABLE).exists()
            else None
        )
        if claimed is None:
            _enqueue()
            claimed = claim_jobs(worker_id=f"worker-{uuid.uuid4().hex[:8]}")[0]
        with patch("jobs.services.get_handler", return_value=handler):
            result = execute_claim(claimed, rng=random.Random(1))
        assert result.state == expected_state
        attempt = JobAttempt.objects.get(id=claimed.attempt.id)
        assert attempt.finished_at is not None


def test_maximum_attempts_turns_retryable_failure_terminal() -> None:
    job = _enqueue(maximum_attempts=1).job
    claimed = claim_jobs(worker_id="worker-one")[0]

    def handler(_context: object) -> HandlerResult:
        raise RetryableJobError

    with patch("jobs.services.get_handler", return_value=handler):
        result = execute_claim(claimed, rng=random.Random(1))
    assert result.id == job.id
    assert result.state == Job.State.FAILED_TERMINAL


def test_cancellation_is_cooperative_and_terminal_jobs_do_not_reopen() -> None:
    queued = _enqueue(available_at=timezone.now() + timedelta(hours=1)).job
    cancelled = request_cancellation(queued.id)
    assert cancelled.state == Job.State.CANCELLED

    running_job = _enqueue().job
    claimed = claim_jobs(worker_id="worker-one")[0]
    requested = request_cancellation(running_job.id)
    assert requested.state == Job.State.CANCELLATION_REQUESTED
    finished = execute_claim(claimed)
    assert finished.state == Job.State.CANCELLED
    with pytest.raises(InvalidJobTransition):
        request_cancellation(finished.id)


def test_expired_lease_recovery_preserves_attempt_and_rejects_old_worker() -> None:
    job = _enqueue().job
    claimed = claim_jobs(worker_id="worker-one", lease_seconds=1)[0]
    future = timezone.now() + timedelta(seconds=2)
    assert recover_expired_leases(now=future) == 1
    job.refresh_from_db()
    assert job.state == Job.State.RETRY_WAIT
    attempt = JobAttempt.objects.get(id=claimed.attempt.id)
    assert attempt.outcome == JobAttempt.Outcome.LEASE_LOST
    with pytest.raises(StaleJobLease):
        execute_claim(claimed)


def test_external_effect_lease_loss_quarantines_instead_of_retrying() -> None:
    job = _enqueue(effect_class="external_ambiguous").job
    claim_jobs(worker_id="worker-one", lease_seconds=1)
    recover_expired_leases(now=timezone.now() + timedelta(seconds=2))
    job.refresh_from_db()
    assert job.state == Job.State.QUARANTINED
    assert job.quarantine_reason == Job.QuarantineReason.LEASE_LOSS


def test_restore_quarantine_changes_only_unfinished_and_invalidates_leases() -> None:
    unfinished = _enqueue().job
    claimed = claim_jobs(worker_id="worker-one")[0]
    succeeded = _enqueue().job
    Job.execution_objects.filter(id=succeeded.id).update(
        state=Job.State.SUCCEEDED, result=Job.Result.SUCCEEDED, finished_at=timezone.now()
    )
    assert quarantine_unfinished_jobs() >= 1
    unfinished.refresh_from_db()
    claimed.job.refresh_from_db()
    succeeded.refresh_from_db()
    assert unfinished.state == Job.State.QUARANTINED
    assert claimed.job.state == Job.State.QUARANTINED
    assert claimed.job.lease_id is None
    assert succeeded.state == Job.State.SUCCEEDED


def test_worker_and_restore_commands_have_bounded_output() -> None:
    output = StringIO()
    call_command("run_worker", once=True, stdout=output)
    assert "worker_iteration" in output.getvalue()
    assert "payload" not in output.getvalue()
    restore_output = StringIO()
    call_command("quarantine_unfinished_jobs", stdout=restore_output)
    assert "unfinished_jobs_quarantined count=" in restore_output.getvalue()
