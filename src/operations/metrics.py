from dataclasses import dataclass

from ai_assistance.models import AIRequest
from jobs.models import Job
from legacy_imports.models import ImportBatch
from scenes.models import Scene, SceneSearchProjection


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    labels: tuple[tuple[str, str], ...]
    value: int


METRIC_DEFINITIONS = (
    "http_requests",
    "job_queue",
    "job_lease_recovery",
    "job_terminal_failure",
    "job_quarantine",
    "authentication_outcome",
    "backup_archive_outcome",
    "restore_readiness_outcome",
    "search_projection_backlog",
    "ai_request_state",
    "import_batch_state",
)


def operational_snapshot() -> tuple[Metric, ...]:
    values: list[Metric] = []
    for state in Job.State.values:
        values.append(
            Metric("jobs", (("state", state),), Job.execution_objects.filter(state=state).count())
        )
    for state in ImportBatch.State.values:
        values.append(
            Metric("imports", (("state", state),), ImportBatch.objects.filter(state=state).count())
        )
    for state in AIRequest.State.values:
        values.append(
            Metric(
                "ai_requests", (("state", state),), AIRequest.objects.filter(state=state).count()
            )
        )
    stale = Scene.objects.exclude(
        current_revision_id__in=SceneSearchProjection.objects.values("source_revision_id")
    ).count()
    values.append(Metric("search_projection_backlog", (), stale))
    return tuple(values)
