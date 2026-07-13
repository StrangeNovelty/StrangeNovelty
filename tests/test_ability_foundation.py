import uuid
from pathlib import Path

from django.db.models.deletion import CASCADE, PROTECT
from django.urls import resolve, reverse

from characters.forms import AbilityEventForm, AbilityForm, AbilityPredictionForm, AbilityStageForm
from characters.models import Ability, AbilityEvent, AbilityPrediction, AbilityStage


def test_ability_schema_is_typed_workspace_owned_and_timestamped() -> None:
    assert {field.name for field in Ability._meta.fields} == {
        "id",
        "workspace",
        "character",
        "name",
        "category",
        "description",
        "limitations",
        "costs",
        "mastery",
        "status",
        "notes",
        "created_at",
        "updated_at",
    }
    for model in (Ability, AbilityStage, AbilityEvent, AbilityPrediction):
        assert model._meta.pk.__class__.__name__ == "UUIDField"
        assert model._meta.get_field("workspace").remote_field.on_delete is PROTECT
        assert model._meta.get_field("created_at") is not None
        assert model._meta.get_field("updated_at") is not None
    for model in (AbilityStage, AbilityEvent, AbilityPrediction):
        assert model._meta.get_field("ability").remote_field.on_delete is CASCADE
    assert AbilityEvent._meta.get_field("scene").remote_field.on_delete is PROTECT


def test_ability_forms_are_small_explicit_and_author_friendly() -> None:
    assert tuple(AbilityForm().fields) == (
        "name",
        "category",
        "description",
        "limitations",
        "costs",
        "mastery",
        "status",
        "notes",
    )
    assert tuple(AbilityStageForm().fields) == (
        "name",
        "order",
        "state",
        "description",
        "requirements",
        "costs",
    )
    assert tuple(AbilityPredictionForm().fields) == (
        "title",
        "prediction",
        "rationale",
        "status",
        "notes",
    )
    assert tuple(AbilityEventForm.base_fields) == (
        "title",
        "event_type",
        "event_date",
        "story_time",
        "description",
        "scene",
    )
    assert tuple(value for value, _ in Ability.Mastery.choices) == (
        "latent",
        "emerging",
        "trained",
        "advanced",
        "mastered",
    )
    assert tuple(value for value, _ in Ability.Status.choices) == (
        "active",
        "dormant",
        "lost",
        "unstable",
        "sealed",
    )


def test_ability_routes_resolve_to_named_views() -> None:
    ids = {name: uuid.uuid4() for name in ("character", "ability", "stage", "event", "prediction")}
    routes = {
        "ability-create": {"character_id": ids["character"]},
        "ability-detail": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
        },
        "ability-delete": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
        },
        "ability-stage-create": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
        },
        "ability-stage-edit": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
            "stage_id": ids["stage"],
        },
        "ability-stage-delete": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
            "stage_id": ids["stage"],
        },
        "ability-event-create": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
        },
        "ability-event-edit": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
            "event_id": ids["event"],
        },
        "ability-event-delete": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
            "event_id": ids["event"],
        },
        "ability-prediction-create": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
        },
        "ability-prediction-edit": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
            "prediction_id": ids["prediction"],
        },
        "ability-prediction-delete": {
            "character_id": ids["character"],
            "ability_id": ids["ability"],
            "prediction_id": ids["prediction"],
        },
    }
    for route_name, kwargs in routes.items():
        assert resolve(reverse(route_name, kwargs=kwargs)).url_name == route_name


def test_ability_templates_separate_history_from_speculation_and_have_no_provider_actions() -> None:
    templates = Path(__file__).parents[1] / "templates/characters"
    detail = (templates / "ability_detail.html").read_text(encoding="utf-8")
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(templates.glob("ability*.html"))
    )
    for copy in (
        "Current Ability",
        "Progression stages",
        "Development history",
        "Private speculation",
        "Predictions are possibilities, not established story canon.",
        "Not canon",
    ):
        assert copy in detail
    assert "provider" not in combined.casefold()
    assert "Suggest next" not in combined
    assert "Estimate endgame" not in combined
    assert "Check progression" not in combined


def test_ability_styles_preserve_focus_overflow_and_narrow_layout_behavior() -> None:
    stylesheet = (Path(__file__).parents[1] / "static/strange_novelty/app.css").read_text(
        encoding="utf-8"
    )
    assert ".character-form-field input:focus" in stylesheet
    assert ".character-form-field textarea:focus" in stylesheet
    assert ".character-form-field select:focus" in stylesheet
    assert ".ability-card h3 a:focus-visible" in stylesheet
    assert "overflow-wrap: anywhere" in stylesheet
    mobile = stylesheet.split("@media (max-width: 48rem)", maxsplit=1)[1]
    assert ".ability-card-body" in mobile
    assert ".ability-detail-grid" in mobile
    assert ".prediction-list" in mobile
    assert ".ability-summary-strip" in mobile
    assert "grid-template-columns: 1fr" in mobile


def test_ability_migration_is_narrow_typed_and_enforces_current_stage() -> None:
    migration = (
        Path(__file__).parents[1]
        / "src/characters/migrations"
        / "0002_ability_abilityevent_abilityprediction_abilitystage_and_more.py"
    ).read_text(encoding="utf-8")
    for model in ("Ability", "AbilityStage", "AbilityEvent", "AbilityPrediction"):
        assert f'name="{model}"' in migration
    assert "unique_current_stage_per_ability" in migration
    assert "PROTECT" in migration
    assert "CASCADE" in migration
    assert "RunPython" not in migration
    assert "RunSQL" not in migration
    for forbidden in ("GenericForeignKey", "ContentType", "JSONField", "embedding"):
        assert forbidden not in migration
