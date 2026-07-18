import hashlib
import json
import urllib.error
import urllib.request
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
        operation = hashlib.sha256(
            (request.instruction + "\0" + request.source_content).encode("utf-8")
        ).hexdigest()[:32]
        proposed = request.source_content
        if request.capability != "scene_revision_suggestion":
            sections = [
                line[2:] for line in request.source_content.splitlines() if line.startswith("- ")
            ]
            proposed = (
                "\n\n".join(
                    f"## {section}\nSynthetic provider response for {request.instruction}."
                    for section in sections[-12:]
                )
                or f"## Creative Response\nSynthetic provider response for {request.instruction}."
            )
        return AdapterResult(
            proposed_text=proposed,
            provider="local_fake",
            model="deterministic-v1",
            operation_identifier=f"fake-{operation}",
            input_units=len(request.source_content) + len(request.instruction),
            output_units=len(proposed),
        )


class OpenRouterAdapter:
    """Minimal OpenRouter-compatible non-streaming Chat Completions adapter."""

    def __init__(self, *, api_key, model, timeout=45, maximum_tokens=4000):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.maximum_tokens = maximum_tokens

    def generate(self, request: AdapterRequest) -> AdapterResult:
        user_content = f"{request.source_content}\n\n## Author Request\n{request.instruction}"
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a non-authoritative creative collaborator. Follow labeled "
                            "context boundaries and the requested output format. When sections "
                            "are requested, use Markdown level-two headings beginning with ##."
                        ),
                    },
                    {
                        "role": "user",
                        "content": user_content,
                    },
                ],
                "max_tokens": self.maximum_tokens,
                "stream": False,
            }
        ).encode()
        http_request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "Strange Novelty",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout) as response:  # noqa: S310
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in (408, 429) or exc.code >= 500:
                raise RetryableAdapterError("Provider is temporarily unavailable.") from exc
            raise TerminalAdapterError("Provider rejected the request.") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            raise RetryableAdapterError("Provider request timed out.") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TerminalAdapterError("Provider returned malformed data.") from exc
        try:
            text = body["choices"][0]["message"]["content"]
            usage = body.get("usage") or {}
        except (KeyError, IndexError, TypeError) as exc:
            raise TerminalAdapterError("Provider response shape is invalid.") from exc
        if not isinstance(text, str) or not text.strip():
            raise TerminalAdapterError("Provider returned no usable content.")
        return AdapterResult(
            text[: request.maximum_output_characters],
            "openrouter",
            body.get("model", self.model),
            str(body.get("id", ""))[:64],
            int(usage.get("prompt_tokens", 0)),
            int(usage.get("completion_tokens", 0)),
        )


class RoutedOpenRouterAdapter:
    """Try an explicitly ordered model route after retryable failures only."""

    def __init__(self, *, api_key, models, timeout=45, maximum_tokens=4000):
        self.adapters = tuple(
            OpenRouterAdapter(
                api_key=api_key,
                model=model,
                timeout=timeout,
                maximum_tokens=maximum_tokens,
            )
            for model in models
        )

    def generate(self, request: AdapterRequest) -> AdapterResult:
        for index, adapter in enumerate(self.adapters):
            try:
                return adapter.generate(request)
            except RetryableAdapterError:
                if index == len(self.adapters) - 1:
                    raise
        raise TerminalAdapterError("No provider model was attempted.")
