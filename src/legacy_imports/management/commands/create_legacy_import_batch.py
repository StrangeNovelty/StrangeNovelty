import uuid
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.http import Http404

from accounts.models import Account
from legacy_imports.parser import LegacyImportError, read_legacy_artifact
from legacy_imports.services import stage_legacy_import
from workspaces.services import get_authorized_workspace


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--account", required=True)
        parser.add_argument("--workspace", required=True)
        parser.add_argument("--source", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            account = Account.objects.get(id=uuid.UUID(options["account"]))
            workspace_id = uuid.UUID(options["workspace"])
            if options["dry_run"]:
                get_authorized_workspace(account, workspace_id)
                artifact = read_legacy_artifact(Path(options["source"]))
                revisions = sum(len(scene.revisions) for scene in artifact.scenes)
                self.stdout.write(
                    f"legacy_import_dry_run scenes={len(artifact.scenes)} revisions={revisions}"
                )
                return
            result = stage_legacy_import(
                account=account,
                workspace_id=workspace_id,
                source_path=Path(options["source"]),
            )
        except (ValueError, Account.DoesNotExist, LegacyImportError, Http404) as exc:
            raise CommandError("Legacy import staging failed safely.") from exc
        self.stdout.write(
            f"legacy_import batch={result.batch.id} state={result.batch.state} "
            f"replayed={str(result.replayed).lower()}"
        )
