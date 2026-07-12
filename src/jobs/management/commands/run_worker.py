import time
import uuid
from argparse import ArgumentParser
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from jobs.services import claim_jobs, execute_claim, recover_expired_leases


class Command(BaseCommand):
    help = "Run the bounded PostgreSQL-backed Job worker."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--once", action="store_true", help="Run one iteration and exit.")
        parser.add_argument("--batch-size", type=int, default=1)
        parser.add_argument("--idle-sleep", type=float, default=1.0)
        parser.add_argument("--worker-id", default=f"worker-{uuid.uuid4().hex[:12]}")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        batch_size = options["batch_size"]
        idle_sleep = options["idle_sleep"]
        worker_id = options["worker_id"]
        if settings.MAINTENANCE_MODE:
            raise CommandError("Worker claiming is disabled during maintenance.")
        if not 1 <= batch_size <= 100 or not 0 <= idle_sleep <= 60:
            raise CommandError("Worker bounds are invalid.")
        try:
            while True:
                recovered = recover_expired_leases()
                claimed = claim_jobs(worker_id=worker_id, batch_size=batch_size)
                for item in claimed:
                    execute_claim(item)
                self.stdout.write(f"worker_iteration recovered={recovered} claimed={len(claimed)}")
                if options["once"]:
                    return
                if not claimed:
                    time.sleep(idle_sleep)
        except KeyboardInterrupt:
            self.stdout.write("worker_stopped")
