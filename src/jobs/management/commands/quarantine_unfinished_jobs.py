from typing import Any

from django.core.management.base import BaseCommand

from jobs.services import quarantine_unfinished_jobs


class Command(BaseCommand):
    help = "Quarantine unfinished Jobs after an isolated restore."

    def handle(self, *args: Any, **options: Any) -> None:
        del args, options
        count = quarantine_unfinished_jobs()
        self.stdout.write(f"unfinished_jobs_quarantined count={count}")
