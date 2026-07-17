import json
from pathlib import Path

import pytest

from ai_assistance.adapters import (
    AdapterRequest,
    DeterministicFakeAdapter,
    OpenRouterAdapter,
    RetryableAdapterError,
)
from ai_assistance.tasks import TASKS


def test_task_registry_covers_visible_creative_workshops():
    categories = {task.category for task in TASKS.values()}
    assert {
        "chat",
        "chapter",
        "scene",
        "character",
        "ability",
        "world",
        "generator",
        "continuity",
        "timeline",
        "deck",
        "voice",
        "editorial",
    } <= categories
    assert TASKS["monster_generate"].conversion_targets
    assert "scene_revision" in TASKS["scene_revision"].conversion_targets


def test_fake_adapter_is_deterministic_and_structured():
    request = AdapterRequest(
        "creative_workspace",
        "Synthetic prompt",
        "## Requested Output Format\n- First\n- Second",
        "synthetic",
        "v1",
        "creative-v1",
        10_000,
    )
    first = DeterministicFakeAdapter().generate(request)
    second = DeterministicFakeAdapter().generate(request)
    assert (
        first == second and "## First" in first.proposed_text and "## Second" in first.proposed_text
    )


def test_openrouter_adapter_parses_usage_and_privacy_safe_errors(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "id": "synthetic-id",
                    "model": "synthetic/model",
                    "choices": [{"message": {"content": "## Result\nSynthetic"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                }
            ).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: Response())
    adapter = OpenRouterAdapter(api_key="synthetic-secret", model="synthetic/model")
    result = adapter.generate(
        AdapterRequest("creative_workspace", "Synthetic", "Context", "task", "v1", "v1", 1000)
    )
    assert result.input_units == 10 and result.output_units == 4 and result.provider == "openrouter"

    def timeout(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr("urllib.request.urlopen", timeout)
    with pytest.raises(RetryableAdapterError, match="timed out"):
        adapter.generate(
            AdapterRequest("creative_workspace", "Synthetic", "Context", "task", "v1", "v1", 1000)
        )


def test_ai_templates_and_docs_do_not_contain_credentials_or_private_content():
    root = Path(__file__).parents[1]
    workspace = (root / "templates/ai_assistance/workspace.html").read_text()
    review = (root / "templates/ai_assistance/creative_review.html").read_text()
    docs = (root / "docs/reference/context-aware-ai.md").read_text()
    assert "creative studio" not in workspace.lower() or "Workshop" in workspace
    assert "Immutable Provider Output" in review and "Explicit Native Conversion" in review
    combined = workspace + review + docs
    assert "OPENROUTER_API_KEY=" not in combined and "Bearer " not in combined
