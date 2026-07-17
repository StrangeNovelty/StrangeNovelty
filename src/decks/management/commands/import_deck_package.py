import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from decks.importing import import_package, load_and_validate_manifest
from workspaces.models import Workspace


class Command(BaseCommand):
    help = "Validate or transactionally import a private native Deck package."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--manifest", required=True, type=Path)
        parser.add_argument("--workspace", required=True)
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--validate-only", action="store_true")
        mode.add_argument("--commit", action="store_true")
        parser.add_argument("--refresh-original-snapshots", action="store_true")

    def handle(self, *args, **options) -> None:
        try:
            workspace = Workspace.objects.get(id=options["workspace"])
        except (Workspace.DoesNotExist, ValueError) as exc:
            raise CommandError("Workspace does not exist.") from exc
        package, validation = load_and_validate_manifest(options["manifest"])
        if package is None:
            self.stdout.write(json.dumps(validation.as_dict(), indent=2))
            raise CommandError("Deck package validation failed.")
        report = import_package(
            package=package,
            workspace=workspace,
            commit=options["commit"],
            refresh_original_snapshots=options["refresh_original_snapshots"],
        )
        self.stdout.write(json.dumps(report.as_dict(), indent=2))
        if options["validate_only"]:
            self.stdout.write(self.style.SUCCESS("Validation completed with no writes."))
        else:
            self.stdout.write(self.style.SUCCESS("Deck package import committed."))
