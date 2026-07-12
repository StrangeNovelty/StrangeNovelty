from typing import Any

from django.core.management.base import BaseCommand

from legacy_imports.services import quarantine_unfinished_imports


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        del args, options
        count = quarantine_unfinished_imports()
        self.stdout.write(f"legacy_import_quarantine count={count}")
