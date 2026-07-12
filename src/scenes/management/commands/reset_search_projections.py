import uuid
from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from scenes.models import Scene, SceneSearchProjection
from scenes.search_indexing import invalidate_and_enqueue_scene_search


class Command(BaseCommand):
    help = "Discard derived Scene search projections after restore or configuration change."

    def add_arguments(self, parser: ArgumentParser) -> None:
        scope = parser.add_mutually_exclusive_group(required=True)
        scope.add_argument("--workspace")
        scope.add_argument("--all-workspaces", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument("--enqueue", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args: Any, **options: Any) -> None:
        del args
        if not options["dry_run"] and not options["confirm"]:
            raise CommandError("Use --confirm or --dry-run.")
        if not 1 <= options["limit"] <= 1000:
            raise CommandError("Reset limit must be between 1 and 1000.")
        projections = SceneSearchProjection.objects.all()
        scenes = Scene.objects.select_related("workspace", "current_revision").filter(
            lifecycle__in=(Scene.Lifecycle.ACTIVE, Scene.Lifecycle.ARCHIVED),
            current_revision__isnull=False,
        )
        if options["workspace"]:
            try:
                workspace_id = uuid.UUID(options["workspace"])
            except ValueError as exc:
                raise CommandError("Workspace identifier is invalid.") from exc
            projections = projections.filter(workspace_id=workspace_id)
            scenes = scenes.filter(workspace_id=workspace_id)
        count = projections.count()
        selected = list(scenes.order_by("workspace_id", "ordering", "id")[: options["limit"]])
        if not options["dry_run"]:
            with transaction.atomic():
                projections.delete()
                if options["enqueue"]:
                    for scene in selected:
                        invalidate_and_enqueue_scene_search(scene, scene.current_revision)
        enqueued = len(selected) if options["enqueue"] and not options["dry_run"] else 0
        self.stdout.write(f"search_projections reset={count} rebuild_enqueued={enqueued}")
