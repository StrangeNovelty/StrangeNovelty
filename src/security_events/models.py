import uuid
from typing import cast

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from security_events.exceptions import ImmutableSecurityEventError
from security_events.managers import SecurityEventManager
from security_events.taxonomy import (
    EVENT_TYPE_CHOICES,
    OUTCOME_CHOICES,
    REASON_CHOICES,
    SERVICE_ROLE_CHOICES,
    TARGET_CHOICES,
)
from workspaces.models import Workspace


class SecurityEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPE_CHOICES)
    outcome = models.CharField(max_length=16, choices=OUTCOME_CHOICES)
    occurred_at = models.DateTimeField(default=timezone.now, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="security_events",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="security_events",
    )
    target_category = models.CharField(max_length=24, choices=TARGET_CHOICES)
    target_id = models.UUIDField(null=True, blank=True)
    correlation_id = models.CharField(max_length=32)
    service_role = models.CharField(max_length=16, choices=SERVICE_ROLE_CHOICES)
    reason = models.CharField(
        max_length=32,
        choices=REASON_CHOICES,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = SecurityEventManager()

    class Meta:
        ordering = ("-occurred_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    event_type__in=(
                        "owner_bootstrap_succeeded",
                        "owner_bootstrap_rejected",
                        "login_succeeded",
                        "login_failed",
                        "logout_succeeded",
                        "workspace_access_denied",
                        "scene_access_denied",
                        "scene_save_conflict",
                        "scene_save_key_conflict",
                    )
                ),
                name="security_event_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(outcome__in=("succeeded", "denied", "conflicted", "failed")),
                name="security_event_outcome_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    target_category__in=(
                        "authentication",
                        "account",
                        "session",
                        "workspace",
                        "scene",
                        "bootstrap",
                    )
                ),
                name="security_event_target_valid",
            ),
            models.CheckConstraint(
                condition=Q(service_role__in=("web", "operator")),
                name="security_event_service_role_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    reason__in=(
                        "",
                        "invalid_credentials",
                        "inaccessible",
                        "inactive_grant",
                        "optimistic_concurrency",
                        "idempotency_key_reuse",
                        "existing_state",
                        "invalid_input",
                    )
                ),
                name="security_event_reason_valid",
            ),
            models.CheckConstraint(
                condition=Q(correlation_id__regex=r"^[0-9a-f]{32}$"),
                name="security_event_correlation_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("event_type", "occurred_at"), name="security_type_time_idx"),
            models.Index(fields=("outcome", "occurred_at"), name="security_outcome_time_idx"),
            models.Index(fields=("workspace", "occurred_at"), name="security_ws_time_idx"),
            models.Index(fields=("actor", "occurred_at"), name="security_actor_time_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.get_event_type_display())

    def save(self, *args: object, **kwargs: object) -> None:
        if not self._state.adding:
            raise ImmutableSecurityEventError("Security Events are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> tuple[int, dict[str, int]]:
        del args, kwargs
        raise ImmutableSecurityEventError("Security Events cannot be deleted.")
