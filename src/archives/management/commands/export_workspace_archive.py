import uuid
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from archives.services import ArchiveError, export_workspace_archive


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--workspace", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--overwrite", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            counts = export_workspace_archive(
                uuid.UUID(options["workspace"]),
                Path(options["output"]),
                overwrite=options["overwrite"],
                dry_run=options["dry_run"],
            )
        except (ValueError, ArchiveError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"workspace_archive records={sum(counts.values())}")
