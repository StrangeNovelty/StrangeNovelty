import uuid
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from archives.services import ArchiveError, export_readable_workspace


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--workspace", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--include-trashed", action="store_true")
        parser.add_argument("--overwrite", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            count = export_readable_workspace(
                uuid.UUID(options["workspace"]),
                Path(options["output"]),
                include_trashed=options["include_trashed"],
                overwrite=options["overwrite"],
                dry_run=options["dry_run"],
            )
        except (ValueError, ArchiveError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"readable_export scenes={count}")
