import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from legacy_imports.models import ImportBatch
from legacy_imports.parser import LegacyImportError
from legacy_imports.services import validate_staged_import_job


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch", required=True)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            batch = ImportBatch.objects.get(id=uuid.UUID(options["batch"]))
            if batch.staging_job_id is None:
                raise LegacyImportError("Import Batch has no validation Job.")
            validate_staged_import_job(str(batch.staging_job_id))
        except (ValueError, ImportBatch.DoesNotExist, LegacyImportError) as exc:
            raise CommandError("Legacy import validation failed safely.") from exc
        self.stdout.write(f"legacy_import_validation batch={batch.id} verified=true")
