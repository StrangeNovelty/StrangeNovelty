from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from jobs.exceptions import TerminalJobError, UnknownJobType


class HandlerOutcome(StrEnum):
    SUCCEEDED = "succeeded"


@dataclass(frozen=True, slots=True)
class JobContext:
    job_id: str
    workspace_id: str | None
    cancellation_requested: Callable[[], bool]


@dataclass(frozen=True, slots=True)
class HandlerResult:
    outcome: HandlerOutcome


JobHandler = Callable[[JobContext], HandlerResult]


def _internal_noop(context: JobContext) -> HandlerResult:
    if context.cancellation_requested():
        raise TerminalJobError("Cancellation requested.")
    return HandlerResult(HandlerOutcome.SUCCEEDED)


def _rebuild_scene_search(context: JobContext) -> HandlerResult:
    from scenes.search_indexing import rebuild_scene_search_projection

    rebuild_scene_search_projection(context.job_id)
    return HandlerResult(HandlerOutcome.SUCCEEDED)


_HANDLERS: dict[str, JobHandler] = {
    "internal_noop": _internal_noop,
    "rebuild_scene_search_projection": _rebuild_scene_search,
}


def get_handler(job_type: str) -> JobHandler:
    try:
        return _HANDLERS[job_type]
    except KeyError as exc:
        raise UnknownJobType("Job type is not registered.") from exc
