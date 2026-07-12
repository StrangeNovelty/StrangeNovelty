import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.http import Http404

from accounts.models import Account
from legacy_imports.parser import LegacyImportError
from legacy_imports.services import approve_import


class Command(BaseCommand):
    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--account", required=True)
        parser.add_argument("--batch", required=True)
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        if not options["confirm"]:
            raise CommandError("Explicit approval confirmation is required.")
        try:
            account = Account.objects.get(id=uuid.UUID(options["account"]))
            batch = approve_import(account=account, batch_id=uuid.UUID(options["batch"]))
        except (ValueError, Account.DoesNotExist, LegacyImportError, Http404) as exc:
            raise CommandError("Legacy import approval failed safely.") from exc
        self.stdout.write(f"legacy_import_approval batch={batch.id} state={batch.state}")
