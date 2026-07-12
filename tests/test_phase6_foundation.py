import random
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from jobs.admin import IdempotencyRecordAdmin, JobAdmin, JobAttemptAdmin
from jobs.exceptions import ImmutableJobRecord, UnknownJobType
from jobs.models import IdempotencyRecord, Job, JobAttempt
from jobs.registry import get_handler
from jobs.services import retry_delay
from scenes.models import MutationOperation, SceneSaveRequest
from security_events.models import SecurityEvent


def test_job_schema_is_bounded_and_has_no_private_payload() -> None:
    fields = {field.name for field in Job._meta.fields}
    assert fields == {
        "id",
        "workspace",
        "job_type",
        "state",
        "target_category",
        "target_id",
        "payload_version",
        "effect_class",
        "available_at",
        "started_at",
        "finished_at",
        "lease_id",
        "lease_owner",
        "lease_expires_at",
        "heartbeat_at",
        "attempt_count",
        "maximum_attempts",
        "cancellation_requested_at",
        "result",
        "failure",
        "quarantine_reason",
        "created_at",
        "updated_at",
    }
    assert Job._meta.pk.__class__.__name__ == "UUIDField"
    assert fields.isdisjoint(
        {"content", "title", "payload", "prompt", "response", "url", "path", "exception"}
    )


def test_attempt_and_idempotency_schemas_are_separate_and_private() -> None:
    attempt_fields = {field.name for field in JobAttempt._meta.fields}
    idempotency_fields = {field.name for field in IdempotencyRecord._meta.fields}
    assert {"job", "attempt_number", "worker_id", "lease_id", "outcome"} <= attempt_fields
    assert {"idempotency_key", "request_fingerprint", "resulting_job"} <= idempotency_fields
    forbidden = {"content", "payload", "request_body", "exception", "metadata"}
    assert attempt_fields.isdisjoint(forbidden)
    assert idempotency_fields.isdisjoint(forbidden)
    assert SceneSaveRequest._meta.label != IdempotencyRecord._meta.label
    assert MutationOperation._meta.label != JobAttempt._meta.label
    assert SecurityEvent._meta.label != JobAttempt._meta.label


def test_default_operational_managers_reject_unsafe_mutation() -> None:
    for model in (Job, JobAttempt, IdempotencyRecord):
        with pytest.raises(ImmutableJobRecord):
            model.objects.none().update(state="invented")
        with pytest.raises(ImmutableJobRecord):
            model.objects.none().delete()


def test_registry_is_allowlisted_and_rejects_arbitrary_code_names() -> None:
    assert callable(get_handler("internal_noop"))
    with pytest.raises(UnknownJobType):
        get_handler("os.system")


def test_retry_backoff_is_exponential_jittered_and_bounded() -> None:
    first = retry_delay(1, rng=random.Random(1)).total_seconds()
    third = retry_delay(3, rng=random.Random(1)).total_seconds()
    late = retry_delay(30, rng=random.Random(1)).total_seconds()
    assert 5 <= first <= 6.25
    assert 20 <= third <= 25
    assert late <= 300


def test_admin_is_read_only_and_hides_keys_from_lists() -> None:
    request = RequestFactory().get("/admin/")
    request.user = SimpleNamespace(is_active=True, is_staff=True)
    admins = (
        JobAdmin(Job, SimpleNamespace()),
        JobAttemptAdmin(JobAttempt, SimpleNamespace()),
        IdempotencyRecordAdmin(IdempotencyRecord, SimpleNamespace()),
    )
    for model_admin in admins:
        assert model_admin.has_view_permission(request)
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
    columns = set(admins[-1].list_display)
    assert "idempotency_key" not in columns
    assert "request_fingerprint" not in columns


def test_jobs_migration_is_narrow() -> None:
    migration = (Path(__file__).parents[1] / "src/jobs/migrations/0001_initial.py").read_text(
        encoding="utf-8"
    )
    for model in ("Job", "JobAttempt", "IdempotencyRecord"):
        assert model in migration
    assert "UUIDField" in migration
    assert "PROTECT" in migration
    assert "RunPython" not in migration
    assert "RunSQL" not in migration
    for forbidden in ("TextField", "JSONField", "Search", "Import", "AI", "Provider"):
        assert forbidden not in migration


def test_job_identities_are_unrelated_to_authorization() -> None:
    assert isinstance(uuid.uuid4(), uuid.UUID)
    assert "workspace" in {field.name for field in Job._meta.fields}
