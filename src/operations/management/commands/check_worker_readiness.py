from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from operations.health import database_ready


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        del args, options
        ready = (
            settings.SERVICE_ROLE == "worker" and not settings.MAINTENANCE_MODE and database_ready()
        )
        self.stdout.write(f"worker_readiness outcome={'pass' if ready else 'fail'}")
        if not ready:
            raise CommandError("Worker is not ready.")
