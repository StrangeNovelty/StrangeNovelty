import json
from pathlib import Path

import pytest

from ai_assistance.adapters import (
    AdapterRequest,
    AdapterResult,
    DeterministicFakeAdapter,
    OpenRouterAdapter,
    RetryableAdapterError,
    RoutedOpenRouterAdapter,
)
from ai_assistance.routing import (
    ANALYSIS,
    BRAINSTORMING,
    OUTLINING,
    TASK_ROUTES,
    WRITING,
    route_for_task,
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
    assert set(TASKS) == set(TASK_ROUTES)


@pytest.mark.parametrize(
    ("task_key", "category"),
    (
        ("scene_rewrite", WRITING),
        ("chapter_outline", OUTLINING),
        ("character_deepen", BRAINSTORMING),
        ("continuity_review", ANALYSIS),
    ),
)
def test_task_model_routing_uses_configurable_categories(settings, task_key, category):
    settings.AI_MODEL = "owner/fallback"
    settings.AI_MODEL_WRITING = "owner/writing"
    settings.AI_MODEL_WRITING_ALTERNATE = "owner/writing-alternate"
    settings.AI_MODEL_OUTLINING = "owner/outlining"
    settings.AI_MODEL_BRAINSTORMING = "owner/brainstorming"
    settings.AI_MODEL_ANALYSIS = "owner/analysis"
    route = route_for_task(task_key)
    assert route.category == category
    assert route.primary == getattr(settings, f"AI_MODEL_{category.upper()}")
    assert route.alternates == (("owner/writing-alternate",) if category == WRITING else ())


def test_task_model_override_preserves_routing_category(settings):
    settings.AI_MODEL = "owner/fallback"
    route = route_for_task("chapter_outline", model_override="owner/custom")
    assert route.category == OUTLINING and route.primary == "owner/custom" and not route.alternates


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
    sent_payload = {}

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

    def urlopen(request, timeout):
        del timeout
        sent_payload.update(json.loads(request.data.decode()))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    adapter = OpenRouterAdapter(api_key="synthetic-secret", model="synthetic/model")
    result = adapter.generate(
        AdapterRequest("creative_workspace", "Synthetic", "Context", "task", "v1", "v1", 1000)
    )
    assert result.input_units == 10 and result.output_units == 4 and result.provider == "openrouter"
    assert "## Author Request\nSynthetic" in sent_payload["messages"][1]["content"]
    assert "level-two headings" in sent_payload["messages"][0]["content"]

    def timeout(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr("urllib.request.urlopen", timeout)
    with pytest.raises(RetryableAdapterError, match="timed out"):
        adapter.generate(
            AdapterRequest("creative_workspace", "Synthetic", "Context", "task", "v1", "v1", 1000)
        )


def test_routed_openrouter_uses_alternate_only_after_retryable_failure(monkeypatch):
    attempts = []

    def generate(adapter, request):
        attempts.append(adapter.model)
        if adapter.model == "owner/primary":
            raise RetryableAdapterError("synthetic retry")
        return AdapterResult("## Result\nSynthetic", "openrouter", adapter.model, "op", 1, 1)

    monkeypatch.setattr(OpenRouterAdapter, "generate", generate)
    adapter = RoutedOpenRouterAdapter(
        api_key="synthetic-secret", models=("owner/primary", "owner/alternate")
    )
    result = adapter.generate(
        AdapterRequest("creative_workspace", "Synthetic", "Context", "task", "v1", "v1", 1000)
    )
    assert attempts == ["owner/primary", "owner/alternate"]
    assert result.model == "owner/alternate"


def test_ai_templates_and_docs_do_not_contain_credentials_or_private_content():
    root = Path(__file__).parents[1]
    workspace = (root / "templates/ai_assistance/workspace.html").read_text()
    review = (root / "templates/ai_assistance/creative_review.html").read_text()
    docs = (root / "docs/reference/context-aware-ai.md").read_text()
    assert "creative studio" not in workspace.lower() or "Workshop" in workspace
    assert "Immutable Provider Output" in review and "Apply to Story" in review
    combined = workspace + review + docs
    assert "OPENROUTER_API_KEY=" not in combined and "Bearer " not in combined
