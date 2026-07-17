from pathlib import Path

from django.urls import reverse

from characters.models import CharacterGroup, GroupRelationship
from worldbuilding.forms import SceneWorldContextForm
from worldbuilding.models import (
    CodexEntry,
    Creature,
    Location,
    Region,
    SceneCreatureLink,
    SceneLocationLink,
    WorldItem,
)

ROOT = Path(__file__).resolve().parents[1]


def test_worldbuilding_uses_explicit_typed_models() -> None:
    assert {Region, Location, CodexEntry, WorldItem, Creature}
    assert SceneLocationLink._meta.get_field("location").related_model is Location
    assert SceneCreatureLink._meta.get_field("creature").related_model is Creature
    assert "content_type" not in {field.name for field in SceneLocationLink._meta.fields}


def test_factions_extend_existing_group_domain() -> None:
    expected = {"alignment", "public_goals", "hidden_goals", "resources", "territory", "history"}
    assert expected.issubset(field.name for field in CharacterGroup._meta.fields)
    assert GroupRelationship._meta.get_field("source").related_model is CharacterGroup


def test_world_routes_and_scene_context_are_explicit() -> None:
    record = "00000000-0000-0000-0000-000000000001"
    scene = "00000000-0000-0000-0000-000000000002"
    assert reverse("world-home") == "/world/"
    assert reverse("world-record-list", args=("locations",)) == "/world/locations/"
    assert reverse("world-record-detail", args=("locations", record)).endswith(f"/{record}/")
    assert reverse("scene-world-context-update", args=(scene,)).endswith("/world-context/")
    assert set(SceneWorldContextForm.base_fields) == {
        "primary_location",
        "locations",
        "regions",
        "groups",
        "codex_entries",
        "items",
        "creatures",
    }


def test_world_templates_cover_empty_state_context_and_accessibility() -> None:
    library = (ROOT / "templates/worldbuilding/list.html").read_text()
    detail = (ROOT / "templates/worldbuilding/detail.html").read_text()
    scene = (ROOT / "templates/scenes/editor.html").read_text()
    css = (ROOT / "static/strange_novelty/app.css").read_text()
    assert "No {{ config.plural }} yet" in library
    assert "Story Connections" in detail
    assert "World Context" in scene and "scene-world-context-update" in scene
    assert "overflow-wrap: anywhere" in css
    assert ".world-record-card:focus-visible" in css
    assert "grid-template-columns: 1fr" in css.split("@media (max-width: 48rem)", 1)[1]
