import hashlib
from dataclasses import dataclass
from typing import Protocol


class AdapterError(Exception):
    pass


class RetryableAdapterError(AdapterError):
    pass


class TerminalAdapterError(AdapterError):
    pass


class AmbiguousAdapterError(AdapterError):
    pass


@dataclass(frozen=True, slots=True)
class AdapterRequest:
    capability: str
    instruction: str
    source_content: str
    prompt_template: str
    prompt_template_version: str
    configuration_version: str
    maximum_output_characters: int


@dataclass(frozen=True, slots=True)
class AdapterResult:
    proposed_text: str
    provider: str
    model: str
    operation_identifier: str
    input_units: int
    output_units: int


class ProviderAdapter(Protocol):
    def generate(self, request: AdapterRequest) -> AdapterResult: ...


class DeterministicFakeAdapter:
    """Local test adapter: deterministic, side-effect free, and intentionally non-production."""

    def generate(self, request: AdapterRequest) -> AdapterResult:
        if request.capability != "scene_revision_suggestion":
            raise TerminalAdapterError("Unsupported capability.")
        operation = hashlib.sha256(
            (request.instruction + "\0" + request.source_content).encode("utf-8")
        ).hexdigest()[:32]
        return AdapterResult(
            proposed_text=request.source_content,
            provider="local_fake",
            model="deterministic-v1",
            operation_identifier=f"fake-{operation}",
            input_units=len(request.source_content) + len(request.instruction),
            output_units=len(request.source_content),
        )
