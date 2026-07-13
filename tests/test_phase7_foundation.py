from pathlib import Path

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.urls import resolve, reverse

from jobs.registry import get_handler
from scenes.models import SceneSearchProjection
from scenes.search import _plain_excerpt
from scenes.search_indexing import (
    PROJECTION_SCHEMA_VERSION,
    SEARCH_CONFIGURATION,
    SEARCH_CONFIGURATION_VERSION,
)


def test_projection_schema_is_current_only_and_derived() -> None:
    fields = {field.name for field in SceneSearchProjection._meta.fields}
    assert fields == {
        "id",
        "workspace",
        "scene",
        "source_revision",
        "source_scene_version",
        "projection_schema_version",
        "search_configuration_version",
        "title_vector",
        "body_vector",
        "source_content_hash",
        "built_at",
    }
    assert isinstance(SceneSearchProjection._meta.get_field("title_vector"), SearchVectorField)
    assert isinstance(SceneSearchProjection._meta.get_field("body_vector"), SearchVectorField)
    assert SceneSearchProjection._meta.get_field("scene").one_to_one
    assert fields.isdisjoint({"snippet", "query", "content", "metadata"})


def test_projection_has_gin_index_and_explicit_versions() -> None:
    assert any(isinstance(index, GinIndex) for index in SceneSearchProjection._meta.indexes)
    assert PROJECTION_SCHEMA_VERSION == "scene-search-v1"
    assert SEARCH_CONFIGURATION_VERSION == "simple-v1"
    assert SEARCH_CONFIGURATION == "simple"


def test_search_job_is_allowlisted_not_dynamic() -> None:
    assert callable(get_handler("rebuild_scene_search_projection"))


def test_plain_excerpt_is_query_time_bounded_text() -> None:
    content = "x" * 180 + "needle" + "y" * 180
    excerpt = _plain_excerpt(content, "needle")
    assert "needle" in excerpt
    assert len(excerpt) <= 242
    assert "<mark>" not in excerpt


def test_private_search_route_has_no_query_parameter_contract() -> None:
    assert resolve(reverse("scene-search")).url_name == "scene-search"
    template = (Path(__file__).parents[1] / "templates/scenes/search.html").read_text()
    assert 'method="post"' in template
    assert "{% csrf_token %}" in template
    assert "<label" in template
    assert "<script" not in template


def test_search_template_uses_application_shell_and_preserves_form_contract() -> None:
    template = (Path(__file__).parents[1] / "templates/scenes/search.html").read_text()
    assert 'class="app-shell"' in template
    assert 'aria-label="Primary navigation"' in template
    assert 'class="nav-link nav-link-active"' in template
    assert '<form class="scene-search-form" method="post"' in template
    assert "action=\"{% url 'scene-search' %}\"" in template
    assert "{% csrf_token %}" in template
    assert "{{ form.query }}" in template
    assert "{{ form.query.errors }}" in template
    assert "{{ form.include_archived }}" in template
    assert "scenes/_form_errors.html" in template
    assert "{% if searched %}" in template
    assert "{% if results %}" in template
    assert "{% url 'scene-editor' result.scene.id %}" in template
    assert 'role="status"' in template
    assert '<main class="workspace-main' not in template


def test_phase7_migrations_have_vectors_without_semantic_search() -> None:
    root = Path(__file__).parents[1]
    migration = (root / "src/scenes/migrations/0003_scenesearchprojection.py").read_text()
    assert "SearchVectorField" in migration
    assert "GinIndex" in migration
    assert "SceneSearchProjection" in migration
    for forbidden in ("JSONField", "snippet", "embedding", "vector database", "AI"):
        assert forbidden not in migration


def test_no_search_query_history_model_exists() -> None:
    assert "SearchQuery" not in {
        model.__name__ for model in SceneSearchProjection._meta.apps.get_models()
    }
