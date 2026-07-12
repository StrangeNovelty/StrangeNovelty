from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from archives.services import ArchiveError, restore_workspace_archive


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--archive", required=True)
        parser.add_argument("--report", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument("--acknowledge-isolated", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            report = restore_workspace_archive(
                Path(options["archive"]),
                Path(options["report"]),
                dry_run=options["dry_run"],
                confirmed=options["confirm"],
                isolated_acknowledged=options["acknowledge_isolated"],
            )
        except ArchiveError as exc:
            raise CommandError(str(exc)) from exc
        verified = str(report["validation_passed"]).lower()
        dry_run = str(report["dry_run"]).lower()
        self.stdout.write(f"archive_restore verified={verified} dry_run={dry_run}")
