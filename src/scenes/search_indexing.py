import hashlib
import json
import uuid

from django.contrib.postgres.search import SearchVector
from django.db import OperationalError, transaction
from django.db.models import Value
from django.utils import timezone

from jobs.exceptions import RetryableJobError
from jobs.models import Job
from jobs.services import enqueue_job
from scenes.models import Scene, SceneRevision, SceneSearchProjection

PROJECTION_SCHEMA_VERSION = "scene-search-v1"
SEARCH_CONFIGURATION_VERSION = "simple-v1"
SEARCH_CONFIGURATION = "simple"
PROJECTION_JOB_VERSION = f"{PROJECTION_SCHEMA_VERSION}:{SEARCH_CONFIGURATION_VERSION}"


def invalidate_and_enqueue_scene_search(scene: Scene, revision: SceneRevision) -> Job:
    SceneSearchProjection.objects.filter(scene=scene).delete()
    payload = {
        "configuration": SEARCH_CONFIGURATION_VERSION,
        "projection": PROJECTION_SCHEMA_VERSION,
        "revision": str(revision.id),
        "scene": str(scene.id),
        "version": scene.version,
        "workspace": str(scene.workspace_id),
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    result = enqueue_job(
        workspace=scene.workspace,
        caller="service",
        caller_reference="scene-search",
        idempotency_key=f"scene-search-{scene.id.hex}-{scene.version}",
        request_fingerprint=fingerprint,
        job_type="rebuild_scene_search_projection",
        target_category="scene",
        target_id=scene.id,
        expected_revision_id=revision.id,
        expected_scene_version=scene.version,
        projection_version=PROJECTION_JOB_VERSION,
    )
    return result.job


def rebuild_scene_search_projection(job_id: str) -> None:
    try:
        job = Job.execution_objects.get(id=uuid.UUID(job_id))
        with transaction.atomic():
            try:
                scene = (
                    Scene.objects.select_for_update()
                    .select_related("workspace", "current_revision")
                    .get(id=job.target_id, workspace_id=job.workspace_id)
                )
            except Scene.DoesNotExist:
                return
            current = scene.current_revision
            if current is None:
                SceneSearchProjection.objects.filter(scene=scene).delete()
                return
            if scene.lifecycle == Scene.Lifecycle.TRASHED:
                SceneSearchProjection.objects.filter(scene=scene).delete()
                return
            if (
                current.id != job.expected_revision_id
                or scene.version != job.expected_scene_version
                or job.projection_version != PROJECTION_JOB_VERSION
            ):
                return
            projection, _ = SceneSearchProjection.objects.update_or_create(
                scene=scene,
                defaults={
                    "workspace": scene.workspace,
                    "source_revision": current,
                    "source_scene_version": scene.version,
                    "projection_schema_version": PROJECTION_SCHEMA_VERSION,
                    "search_configuration_version": SEARCH_CONFIGURATION_VERSION,
                    "title_vector": "",
                    "body_vector": "",
                    "source_content_hash": current.content_sha256,
                    "built_at": timezone.now(),
                },
            )
            SceneSearchProjection.objects.filter(id=projection.id).update(
                title_vector=SearchVector(
                    Value(scene.title), config=SEARCH_CONFIGURATION, weight="A"
                ),
                body_vector=SearchVector(
                    Value(current.content), config=SEARCH_CONFIGURATION, weight="B"
                ),
            )
    except OperationalError as exc:
        raise RetryableJobError("Search projection storage is temporarily unavailable.") from exc
