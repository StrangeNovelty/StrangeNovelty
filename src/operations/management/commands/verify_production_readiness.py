from argparse import ArgumentParser
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from jobs.registry import get_handler
from operations.health import database_ready
from operations.readiness import mfa_configuration_ready, owner_mfa_ready, static_readiness_checks


class Command(BaseCommand):
    help = "Verify bounded local production-readiness conditions without deployment."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--static", action="store_true", dest="static_only")
        parser.add_argument("--private-content", action="store_true")
        parser.add_argument("--allow-maintenance", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        checks = static_readiness_checks()
        checks["job_handlers"] = all(
            get_handler(value) is not None
            for value in (
                "internal_noop",
                "rebuild_scene_search_projection",
                "validate_legacy_import",
                "generate_ai_scene_suggestion",
            )
        )
        checks["maintenance_state"] = not settings.MAINTENANCE_MODE or options["allow_maintenance"]
        if not options["static_only"]:
            checks["database_and_migrations"] = database_ready()
        if options["private_content"]:
            checks["mfa_private_content_gate"] = mfa_configuration_ready()
            if not options["static_only"]:
                checks["mfa_owner_enrollment"] = owner_mfa_ready()
        for name, passed in sorted(checks.items()):
            self.stdout.write(f"readiness check={name} outcome={'pass' if passed else 'fail'}")
        if not all(checks.values()):
            raise CommandError("Production readiness checks failed.")
        self.stdout.write("readiness overall=pass deployment_performed=false")
