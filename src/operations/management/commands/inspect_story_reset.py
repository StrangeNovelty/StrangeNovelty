import json
import uuid
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from operations.story_reset import ResetAction, StoryResetInventoryError, inspect_story_reset


class Command(BaseCommand):
    help = "Inspect a proposed Workspace story-content reset without changing any records."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--workspace", required=True)
        parser.add_argument("--format", choices=("text", "json"), default="text")
        parser.add_argument("--include-zero", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        try:
            workspace_id = uuid.UUID(options["workspace"])
            inventory = inspect_story_reset(workspace_id)
        except (ValueError, StoryResetInventoryError) as exc:
            raise CommandError(str(exc)) from exc

        if options["format"] == "json":
            self.stdout.write(json.dumps(inventory.as_dict(), indent=2, sort_keys=True))
            return

        self.stdout.write(
            f"story_reset_inventory workspace={workspace_id} mode=read-only"
        )
        for action in ResetAction:
            self.stdout.write(f"{action.value} total={inventory.total_for(action)}")
            for row in inventory.rows_for(action):
                if row.count == 0 and not options["include_zero"]:
                    continue
                count = "unscoped" if row.count is None else str(row.count)
                self.stdout.write(f"  {row.label}={count}")
        self.stdout.write("No records were changed. This command has no destructive mode.")
