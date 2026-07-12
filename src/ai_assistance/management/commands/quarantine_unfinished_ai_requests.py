from typing import Any

from django.core.management.base import BaseCommand

from ai_assistance.services import quarantine_unfinished_ai_requests


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        del args, options
        count = quarantine_unfinished_ai_requests()
        self.stdout.write(f"ai_request_quarantine count={count}")
