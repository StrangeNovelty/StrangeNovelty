import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from legacy_imports.models import ImportBatch, ImportFinding


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            batch = ImportBatch.objects.get(id=uuid.UUID(options["batch"]))
        except (ValueError, ImportBatch.DoesNotExist) as exc:
            raise CommandError("Import Batch is unavailable.") from exc
        counts = {
            severity: batch.findings.filter(severity=severity).count()
            for severity in ImportFinding.Severity.values
        }
        summary = " ".join(f"{key}={counts[key]}" for key in sorted(counts))
        self.stdout.write(
            f"legacy_import_report batch={batch.id} state={batch.state} "
            f"accepted={batch.accepted_count} transformed={batch.transformed_count} "
            f"warnings={batch.warning_count} rejected={batch.rejected_count} {summary}"
        )
