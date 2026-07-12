import uuid
from argparse import ArgumentParser
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.assurance import revoke_assurance
from accounts.models import (
    Account,
    RecoveryCode,
    RecoveryEnrollment,
    SessionAssurance,
    TOTPCredential,
    WebAuthnCredential,
)
from security_events.services import SecurityEventSpec, record_security_event
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)
from workspaces.models import Workspace, WorkspaceGrant


class Command(BaseCommand):
    help = "Initiate bounded operator-assisted owner MFA recovery."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--account", required=True)
        parser.add_argument("--workspace", required=True)
        parser.add_argument("--confirm", action="store_true")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not options["confirm"]:
            raise CommandError("Explicit --confirm is required.")
        try:
            account = Account.objects.get(id=options["account"], is_active=True)
            workspace = Workspace.objects.get(id=options["workspace"])
            WorkspaceGrant.objects.get(
                account=account,
                workspace=workspace,
                role=WorkspaceGrant.Role.OWNER,
                state=WorkspaceGrant.State.ACTIVE,
            )
        except (Account.DoesNotExist, Workspace.DoesNotExist, WorkspaceGrant.DoesNotExist) as exc:
            raise CommandError(
                "The requested active owner boundary is not unique and valid."
            ) from exc
        now = timezone.now()
        for assurance in SessionAssurance.objects.filter(account=account, revoked_at__isnull=True):
            revoke_assurance(assurance, "owner_recovery")
        WebAuthnCredential.objects.filter(
            account=account, state=WebAuthnCredential.State.ACTIVE
        ).update(state=WebAuthnCredential.State.REVOKED, revoked_at=now)
        TOTPCredential.objects.filter(
            account=account, state__in=(TOTPCredential.State.ACTIVE, TOTPCredential.State.PENDING)
        ).update(state=TOTPCredential.State.REVOKED, revoked_at=now)
        RecoveryCode.objects.filter(
            account=account, used_at__isnull=True, revoked_at__isnull=True
        ).update(revoked_at=now)
        RecoveryEnrollment.objects.filter(
            account=account, used_at__isnull=True, revoked_at__isnull=True
        ).update(revoked_at=now)
        RecoveryEnrollment.objects.create(account=account, expires_at=now + timedelta(minutes=30))
        record_security_event(
            SecurityEventSpec(
                event_type=SecurityEventType.OWNER_RECOVERY_INITIATED,
                outcome=SecurityOutcome.SUCCEEDED,
                actor=account,
                workspace=workspace,
                target_category=SecurityTargetCategory.ACCOUNT,
                target_id=account.id,
                correlation_id=uuid.uuid4().hex,
                service_role=SecurityServiceRole.OPERATOR,
                reason=SecurityReason.RECOVERY,
            )
        )
        self.stdout.write(
            "owner recovery initiated; sessions and factors revoked; "
            "re-enrollment expires in 30 minutes"
        )
