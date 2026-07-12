from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from archives.services import ArchiveError, verify_restore_readiness


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--report", required=True)
        parser.add_argument("--acknowledge-operational-checks", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            ready = verify_restore_readiness(
                Path(options["report"]),
                operational_checks_acknowledged=options["acknowledge_operational_checks"],
            )
        except ArchiveError as exc:
            raise CommandError(str(exc)) from exc
        if not ready:
            raise CommandError("Restore verification is incomplete; activation is not ready.")
        self.stdout.write("restore_readiness verified=true")
