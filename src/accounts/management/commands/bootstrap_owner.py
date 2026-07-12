import getpass
import os
import uuid
from argparse import ArgumentParser
from typing import Any, cast

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from accounts.models import Account
from security_events.services import (
    SecurityEventSpec,
    new_correlation_id,
    record_security_event,
)
from security_events.taxonomy import (
    SecurityEventType,
    SecurityOutcome,
    SecurityReason,
    SecurityServiceRole,
    SecurityTargetCategory,
)
from workspaces.models import OwnerBootstrap, Workspace, WorkspaceGrant

INITIAL_BOOTSTRAP_ID = uuid.UUID("8f603cf7-569d-4c63-9d78-61ecdfaacdd7")


class Command(BaseCommand):
    help = "Create the one initial owner Account, Workspace, and active owner Grant."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--email", required=True, help="Initial owner email address.")
        parser.add_argument(
            "--workspace-name", required=True, help="Initial Workspace display name."
        )
        parser.add_argument(
            "--no-input",
            action="store_true",
            help="Read the password from an ephemeral environment variable.",
        )
        parser.add_argument(
            "--password-env",
            default="STRANGE_NOVELTY_BOOTSTRAP_PASSWORD",
            help="Environment variable name used with --no-input.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        email = self._validated_email(options["email"])
        workspace_name = self._validated_workspace_name(options["workspace_name"])

        existing = self._existing_bootstrap()
        if existing is not None:
            self._report_existing(existing, email, workspace_name)
            return

        if self._application_state_exists():
            self._record_rejection(SecurityReason.EXISTING_STATE)
            raise CommandError(
                "Bootstrap refused because Account, Workspace, or Grant state already exists."
            )

        password = self._read_password(options)
        candidate = Account(email=email)
        try:
            validate_password(password, user=candidate)
        except ValidationError as exc:
            self._record_rejection(
                SecurityReason.INVALID_INPUT,
                outcome=SecurityOutcome.FAILED,
            )
            raise CommandError("The supplied password does not satisfy password policy.") from exc

        try:
            with transaction.atomic():
                existing = OwnerBootstrap.objects.select_for_update().first()
                if existing is not None:
                    self._ensure_same(existing, email, workspace_name)
                    return
                if self._application_state_exists():
                    raise CommandError(
                        "Bootstrap refused because application state appeared concurrently."
                    )

                account = Account.objects.create_user(email=email, password=password)
                workspace = Workspace.objects.create(name=workspace_name)
                WorkspaceGrant.objects.create(
                    account=account,
                    workspace=workspace,
                    role=WorkspaceGrant.Role.OWNER,
                    state=WorkspaceGrant.State.ACTIVE,
                )
                OwnerBootstrap.objects.create(
                    id=INITIAL_BOOTSTRAP_ID,
                    account=account,
                    workspace=workspace,
                )
                record_security_event(
                    SecurityEventSpec(
                        event_type=SecurityEventType.OWNER_BOOTSTRAP_SUCCEEDED,
                        outcome=SecurityOutcome.SUCCEEDED,
                        actor=account,
                        workspace=workspace,
                        target_category=SecurityTargetCategory.BOOTSTRAP,
                        target_id=INITIAL_BOOTSTRAP_ID,
                        correlation_id=new_correlation_id(),
                        service_role=SecurityServiceRole.OPERATOR,
                    ),
                    required=True,
                )
        except IntegrityError as exc:
            existing = self._existing_bootstrap()
            if existing is not None:
                self._report_existing(existing, email, workspace_name)
                return
            raise CommandError("Bootstrap failed without creating partial state.") from exc

        self.stdout.write(self.style.SUCCESS("Owner bootstrap completed successfully."))

    @staticmethod
    def _validated_email(raw_email: str) -> str:
        email = Account.objects.normalize_login_email(raw_email)
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError("A valid owner email is required.") from exc
        return email

    @staticmethod
    def _validated_workspace_name(raw_name: str) -> str:
        name = raw_name.strip()
        maximum = Workspace._meta.get_field("name").max_length
        if not name or maximum is None or len(name) > maximum:
            raise CommandError("A valid Workspace name is required.")
        return name

    @staticmethod
    def _read_password(options: dict[str, Any]) -> str:
        if options["no_input"]:
            variable_name = options["password_env"]
            password = os.environ.get(variable_name, "")
            if not password:
                raise CommandError(
                    "The configured bootstrap password environment variable is missing."
                )
            return password

        first = getpass.getpass("Owner password: ")
        second = getpass.getpass("Confirm owner password: ")
        if not first or first != second:
            raise CommandError("Password confirmation did not match.")
        return first

    @staticmethod
    def _application_state_exists() -> bool:
        return cast(
            bool,
            Account.objects.exists()
            or Workspace.objects.exists()
            or WorkspaceGrant.objects.exists(),
        )

    @staticmethod
    def _existing_bootstrap() -> OwnerBootstrap | None:
        return cast(
            OwnerBootstrap | None,
            OwnerBootstrap.objects.select_related("account", "workspace")
            .filter(id=INITIAL_BOOTSTRAP_ID)
            .first(),
        )

    def _report_existing(self, existing: OwnerBootstrap, email: str, workspace_name: str) -> None:
        try:
            self._ensure_same(existing, email, workspace_name)
        except CommandError:
            self._record_rejection(
                SecurityReason.EXISTING_STATE,
                actor=existing.account,
                workspace=existing.workspace,
            )
            raise
        self.stdout.write("Owner bootstrap is already complete; no changes were made.")

    @staticmethod
    def _ensure_same(existing: OwnerBootstrap, email: str, workspace_name: str) -> None:
        if existing.account.email != email or existing.workspace.name != workspace_name:
            raise CommandError("Bootstrap conflicts with the existing initial owner state.")

    @staticmethod
    def _record_rejection(
        reason: SecurityReason,
        *,
        outcome: SecurityOutcome = SecurityOutcome.CONFLICTED,
        actor: Account | None = None,
        workspace: Workspace | None = None,
    ) -> None:
        record_security_event(
            SecurityEventSpec(
                event_type=SecurityEventType.OWNER_BOOTSTRAP_REJECTED,
                outcome=outcome,
                actor=actor,
                workspace=workspace,
                target_category=SecurityTargetCategory.BOOTSTRAP,
                correlation_id=new_correlation_id(),
                service_role=SecurityServiceRole.OPERATOR,
                reason=reason,
            )
        )
