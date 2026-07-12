import uuid
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.http import Http404

from accounts.models import Account
from legacy_imports.parser import LegacyImportError
from legacy_imports.services import apply_import


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--account", required=True)
        parser.add_argument("--batch", required=True)
        parser.add_argument("--source", required=True)
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument("--acknowledge-nonempty", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        if not options["confirm"]:
            raise CommandError("Explicit apply confirmation is required.")
        try:
            account = Account.objects.get(id=uuid.UUID(options["account"]))
            batch = apply_import(
                account=account,
                batch_id=uuid.UUID(options["batch"]),
                source_path=Path(options["source"]),
                acknowledge_nonempty=options["acknowledge_nonempty"],
            )
        except (
            ValueError,
            Account.DoesNotExist,
            LegacyImportError,
            Http404,
            IntegrityError,
        ) as exc:
            raise CommandError("Legacy import application failed safely.") from exc
        self.stdout.write(f"legacy_import_apply batch={batch.id} state={batch.state}")
