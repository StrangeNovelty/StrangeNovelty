from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from archives.services import ArchiveError, validate_workspace_archive


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--archive", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            result = validate_workspace_archive(Path(options["archive"]))
        except ArchiveError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"archive_valid records={sum(result.counts.values())}")
