import uuid
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from scenes.models import Scene
from scenes.search_indexing import invalidate_and_enqueue_scene_search


class Command(BaseCommand):
    help = "Enqueue bounded Scene search projection rebuild Jobs."

    def add_arguments(self, parser: ArgumentParser) -> None:
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument("--workspace")
        scope.add_argument("--all-workspaces", action="store_true")
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        limit = options["limit"]
        if not 1 <= limit <= 1000:
            raise CommandError("Rebuild limit must be between 1 and 1000.")
        scenes = Scene.objects.select_related("workspace", "current_revision").filter(
            lifecycle__in=(Scene.Lifecycle.ACTIVE, Scene.Lifecycle.ARCHIVED),
            current_revision__isnull=False,
        )
        if options["workspace"]:
            try:
                workspace_id = uuid.UUID(options["workspace"])
            except ValueError as exc:
                raise CommandError("Workspace identifier is invalid.") from exc
            scenes = scenes.filter(workspace_id=workspace_id)
        selected = list(scenes.order_by("workspace_id", "ordering", "id")[:limit])
        if not options["dry_run"]:
            for scene in selected:
                invalidate_and_enqueue_scene_search(scene, scene.current_revision)
        self.stdout.write(
            f"search_rebuild {'planned' if options['dry_run'] else 'enqueued'}={len(selected)}"
        )
