import logging
import re
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from scenes.admin import MutationOperationAdmin
from scenes.exceptions import ImmutableMutationOperationError
from scenes.models import MutationOperation
from security_events.admin import SecurityEventAdmin
from security_events.exceptions import ImmutableSecurityEventError
from security_events.middleware import RequestCorrelationMiddleware
from security_events.models import SecurityEvent
from security_events.services import (
    SecurityEventSpec,
    new_correlation_id,
    record_security_event,
    validated_correlation_id,
)
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)


def test_security_event_schema_is_bounded_and_private() -> None:
    fields = {field.name for field in SecurityEvent._meta.fields}
    assert fields == {
        "id",
        "event_type",
        "outcome",
        "occurred_at",
        "actor",
        "workspace",
        "target_category",
        "target_id",
        "correlation_id",
        "service_role",
        "reason",
        "created_at",
    }
    assert SecurityEvent._meta.pk.__class__.__name__ == "UUIDField"
    forbidden = {
        "content",
        "title",
        "email",
        "password",
        "session",
        "csrf",
        "ip_address",
        "user_agent",
        "metadata",
        "payload",
        "request_body",
        "exception",
        "url",
    }
    assert fields.isdisjoint(forbidden)


def test_security_taxonomy_is_narrow_and_explicit() -> None:
    assert len(SecurityEventType) == 9
    assert set(SecurityOutcome) == {"succeeded", "denied", "conflicted", "failed"}
    assert len(SecurityTargetCategory) == 6
    assert set(SecurityServiceRole) == {"web", "operator"}
    assert len(SecurityReason) == 8


def test_correlation_is_random_bounded_and_validated() -> None:
    first = new_correlation_id()
    second = new_correlation_id()
    assert first != second
    assert re.fullmatch(r"[0-9a-f]{32}", first)
    assert validated_correlation_id(first) == first
    replacement = validated_correlation_id("owner@example.invalid-private-value")
    assert replacement != "owner@example.invalid-private-value"
    assert re.fullmatch(r"[0-9a-f]{32}", replacement)


def test_correlation_middleware_replaces_all_browser_values() -> None:
    seen: list[str] = []

    def endpoint(request: HttpRequest) -> HttpResponse:
        seen.append(cast(str, request.correlation_id))
        return HttpResponse("ok")

    middleware = RequestCorrelationMiddleware(endpoint)
    safe = uuid.uuid4().hex
    request = RequestFactory().get("/health/", HTTP_X_REQUEST_ID=safe)
    response = middleware(request)
    assert seen[-1] != safe
    assert response.headers["X-Request-ID"] == seen[-1]

    invalid = RequestFactory().get("/health/", HTTP_X_REQUEST_ID="private-unbounded-value")
    replaced = middleware(invalid)
    assert replaced.headers["X-Request-ID"] != "private-unbounded-value"
    assert re.fullmatch(r"[0-9a-f]{32}", replaced.headers["X-Request-ID"])


def test_recording_service_rejects_invalid_correlation_before_database() -> None:
    spec = SecurityEventSpec(
        event_type=SecurityEventType.LOGIN_FAILED,
        outcome=SecurityOutcome.DENIED,
        target_category=SecurityTargetCategory.AUTHENTICATION,
        correlation_id="invalid",
        service_role=SecurityServiceRole.WEB,
        reason=SecurityReason.INVALID_CREDENTIALS,
    )
    with pytest.raises(ValueError, match="correlation"):
        record_security_event(spec)


def test_optional_recording_failure_logs_only_bounded_classification(
    caplog: pytest.LogCaptureFixture,
) -> None:
    correlation_id = uuid.uuid4().hex
    spec = SecurityEventSpec(
        event_type=SecurityEventType.LOGIN_FAILED,
        outcome=SecurityOutcome.DENIED,
        target_category=SecurityTargetCategory.AUTHENTICATION,
        correlation_id=correlation_id,
        service_role=SecurityServiceRole.WEB,
        reason=SecurityReason.INVALID_CREDENTIALS,
    )
    with (
        patch.object(SecurityEvent.objects, "create", side_effect=DatabaseError("private")),
        caplog.at_level(logging.WARNING, logger="strange_novelty.security"),
    ):
        assert record_security_event(spec) is None
    assert caplog.messages == ["security_event_recording_failed"]
    assert "private" not in caplog.text


def test_security_event_and_mutation_operation_reject_instance_mutation() -> None:
    event = SecurityEvent(
        event_type=SecurityEventType.LOGIN_FAILED,
        outcome=SecurityOutcome.DENIED,
        target_category=SecurityTargetCategory.AUTHENTICATION,
        correlation_id=uuid.uuid4().hex,
        service_role=SecurityServiceRole.WEB,
        reason=SecurityReason.INVALID_CREDENTIALS,
    )
    event._state.adding = False
    with pytest.raises(ImmutableSecurityEventError):
        event.save()
    with pytest.raises(ImmutableSecurityEventError):
        event.delete()

    operation = MutationOperation()
    operation._state.adding = False
    with pytest.raises(ImmutableMutationOperationError):
        operation.save()
    with pytest.raises(ImmutableMutationOperationError):
        operation.delete()


def test_read_only_admin_has_no_mutation_permissions_or_private_list_fields() -> None:
    request = RequestFactory().get("/admin/")
    request.user = SimpleNamespace(is_active=True, is_staff=True)
    event_admin = SecurityEventAdmin(SecurityEvent, admin_site=SimpleNamespace())
    operation_admin = MutationOperationAdmin(MutationOperation, admin_site=SimpleNamespace())
    for model_admin in (event_admin, operation_admin):
        assert model_admin.has_view_permission(request)
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
    event_columns = set(event_admin.list_display)
    assert event_columns.isdisjoint({"actor", "workspace", "target_id", "correlation_id"})
    assert set(operation_admin.list_display) == {"operation_type", "source", "created_at"}


def test_security_event_migration_is_narrow() -> None:
    migration = (
        Path(__file__).parents[1] / "src/security_events/migrations/0001_initial.py"
    ).read_text(encoding="utf-8")
    assert "CreateModel" in migration
    assert "SecurityEvent" in migration
    assert "UUIDField" in migration
    assert "PROTECT" in migration
    assert "RunPython" not in migration
    assert "RunSQL" not in migration
    for forbidden in ("JSONField", "TextField", "Job", "Search", "Import", "AI", "MFA"):
        assert forbidden not in migration
