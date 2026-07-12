from pathlib import Path

import pytest
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from ai_assistance.adapters import AdapterRequest, DeterministicFakeAdapter
from ai_assistance.models import (
    AIContextManifest,
    AIRequest,
    AISuggestion,
    AISuggestionApplication,
    ProviderEffect,
)


def test_ai_models_use_uuid_and_separate_private_boundaries() -> None:
    for model in (
        AIRequest,
        AIContextManifest,
        AISuggestion,
        AISuggestionApplication,
        ProviderEffect,
    ):
        assert model._meta.pk.get_internal_type() == "UUIDField"
        fields = {field.name for field in model._meta.fields}
        assert not fields & {"secret", "credentials", "payload", "metadata", "vector", "tool"}
    request_fields = {field.name for field in AIRequest._meta.fields}
    suggestion_fields = {field.name for field in AISuggestion._meta.fields}
    assert {"source_revision", "source_scene_version", "source_content_hash"} <= request_fields
    assert {"original_output", "review_text", "resulting_revision"} <= suggestion_fields
    assert "instruction" not in {field.name for field in ProviderEffect._meta.fields}


def test_fake_adapter_is_deterministic_and_side_effect_free() -> None:
    request = AdapterRequest(
        capability="scene_revision_suggestion",
        instruction="Synthetic test instruction",
        source_content="",
        prompt_template="scene-review",
        prompt_template_version="v1",
        configuration_version="ai-scene-v1",
        maximum_output_characters=100,
    )
    adapter = DeterministicFakeAdapter()
    assert adapter.generate(request) == adapter.generate(request)
    assert adapter.generate(request).proposed_text == ""
    assert adapter.generate(request).provider == "local_fake"


def test_ai_admin_is_read_only_and_excludes_private_fields() -> None:
    for model in (
        AIRequest,
        AIContextManifest,
        AISuggestion,
        AISuggestionApplication,
        ProviderEffect,
    ):
        model_admin = admin.site._registry[model]
        assert model_admin.has_add_permission(None) is False
        assert model_admin.has_change_permission(None) is False
        assert model_admin.has_delete_permission(None) is False
    assert {"instruction", "instruction_hash", "request_fingerprint", "idempotency_key"} <= set(
        admin.site._registry[AIRequest].exclude
    )
    assert {"original_output", "review_text", "provider_operation_identifier"} <= set(
        admin.site._registry[AISuggestion].exclude
    )


def test_templates_and_urls_do_not_put_private_ai_input_in_paths() -> None:
    root = Path(__file__).parents[1]
    urls = (root / "src/strange_novelty/urls.py").read_text()
    review = (root / "templates/ai_assistance/review.html").read_text()
    assert "instruction" not in urls
    assert "original_output" in review
    assert "review_text" in review
    assert "force" not in review.casefold()


def test_production_ai_enablement_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("AI_ADAPTER", "local_fake")
    monkeypatch.setenv("STRANGE_NOVELTY_ENV", "production")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "x" * 64)
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.invalid")
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://example.invalid")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://placeholder:placeholder@postgresql.invalid/database"
    )
    with pytest.raises(ImproperlyConfigured):
        import importlib

        import strange_novelty.settings.production as production

        importlib.reload(production)
