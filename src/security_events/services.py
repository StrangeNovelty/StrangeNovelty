import logging
import re
import uuid
from dataclasses import dataclass
from typing import cast

from django.db import DatabaseError

from accounts.models import Account
from security_events.models import SecurityEvent
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)
from workspaces.models import Workspace

CORRELATION_PATTERN = re.compile(r"^[0-9a-f]{32}$")
logger = logging.getLogger("strange_novelty.security")


@dataclass(frozen=True, slots=True)
class SecurityEventSpec:
    event_type: SecurityEventType
    outcome: SecurityOutcome
    target_category: SecurityTargetCategory
    correlation_id: str
    service_role: SecurityServiceRole
    reason: SecurityReason = SecurityReason.NONE
    actor: Account | None = None
    workspace: Workspace | None = None
    target_id: uuid.UUID | None = None


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def validated_correlation_id(candidate: str | None) -> str:
    if candidate is not None and CORRELATION_PATTERN.fullmatch(candidate):
        return candidate
    return new_correlation_id()


def record_security_event(
    spec: SecurityEventSpec,
    *,
    required: bool = False,
) -> SecurityEvent | None:
    _validate_spec(spec)
    try:
        return cast(
            SecurityEvent,
            SecurityEvent.objects.create(
                event_type=spec.event_type,
                outcome=spec.outcome,
                actor=spec.actor,
                workspace=spec.workspace,
                target_category=spec.target_category,
                target_id=spec.target_id,
                correlation_id=spec.correlation_id,
                service_role=spec.service_role,
                reason=spec.reason,
            ),
        )
    except DatabaseError:
        logger.warning(
            "security_event_recording_failed",
            extra={
                "event_name": "security_event_recording_failed",
                "service_role": str(spec.service_role),
                "correlation_id": spec.correlation_id,
            },
        )
        if required:
            raise
        return None


def _validate_spec(spec: SecurityEventSpec) -> None:
    if not isinstance(spec.event_type, SecurityEventType):
        raise ValueError("Invalid security event type.")
    if not isinstance(spec.outcome, SecurityOutcome):
        raise ValueError("Invalid security event outcome.")
    if not isinstance(spec.target_category, SecurityTargetCategory):
        raise ValueError("Invalid security event target category.")
    if not isinstance(spec.service_role, SecurityServiceRole):
        raise ValueError("Invalid security event service role.")
    if not isinstance(spec.reason, SecurityReason):
        raise ValueError("Invalid security event reason.")
    if not CORRELATION_PATTERN.fullmatch(spec.correlation_id):
        raise ValueError("Invalid correlation identifier.")
