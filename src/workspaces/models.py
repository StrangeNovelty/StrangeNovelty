import uuid
from typing import cast

from django.conf import settings
from django.db import models
from django.db.models import Q


class Workspace(models.Model):
    """Private authorization root; contains no creative content in Phase 2."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.CheckConstraint(condition=~Q(name=""), name="workspace_name_not_empty")
        ]

    def __str__(self) -> str:
        return cast(str, self.name)


class WorkspaceGrant(models.Model):
    """Explicit Account-to-Workspace authorization; possession grants nothing."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="grants")
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workspace_grants",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("workspace_id", "account_id", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("account", "workspace"),
                condition=Q(state="active"),
                name="unique_active_account_workspace_grant",
            ),
            models.CheckConstraint(
                condition=(
                    Q(state="active", revoked_at__isnull=True)
                    | Q(state="revoked", revoked_at__isnull=False)
                ),
                name="workspace_grant_state_timestamp_consistent",
            ),
        ]
        indexes = [
            models.Index(fields=("account", "state"), name="grant_account_state_idx"),
            models.Index(fields=("workspace", "state"), name="grant_workspace_state_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_role_display()} grant ({self.get_state_display()})"


class OwnerBootstrap(models.Model):
    """Singleton completion evidence for the protected initial-owner bootstrap."""

    id = models.UUIDField(primary_key=True, editable=False)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owner_bootstrap",
    )
    workspace = models.OneToOneField(
        Workspace,
        on_delete=models.PROTECT,
        related_name="owner_bootstrap",
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "owner bootstrap completion"
        verbose_name_plural = "owner bootstrap completions"

    def __str__(self) -> str:
        return "Initial owner bootstrap completion"
