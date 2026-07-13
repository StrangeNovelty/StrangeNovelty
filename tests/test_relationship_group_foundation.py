import uuid
from pathlib import Path

from django.db.models.deletion import CASCADE, PROTECT
from django.urls import resolve, reverse

from characters.models import CharacterGroup, CharacterRelationship, GroupMembership


def test_connected_cast_models_are_typed_and_workspace_owned() -> None:
    assert {field.name for field in CharacterRelationship._meta.fields} == {
        "id",
        "workspace",
        "source",
        "target",
        "relationship_type",
        "short_label",
        "summary",
        "source_perspective",
        "target_perspective",
        "status",
        "knowledge_state",
        "notes",
        "created_at",
        "updated_at",
    }
    assert CharacterRelationship._meta.get_field("source").remote_field.on_delete is PROTECT
    assert CharacterRelationship._meta.get_field("target").remote_field.on_delete is PROTECT
    assert GroupMembership._meta.get_field("character").remote_field.on_delete is PROTECT
    assert GroupMembership._meta.get_field("group").remote_field.on_delete is CASCADE
    assert CharacterGroup._meta.pk.__class__.__name__ == "UUIDField"


def test_connected_cast_constraints_are_explicit() -> None:
    relationship_constraints = {
        constraint.name for constraint in CharacterRelationship._meta.constraints
    }
    membership_constraints = {constraint.name for constraint in GroupMembership._meta.constraints}
    assert "relationship_pair_canonical" in relationship_constraints
    assert "unique_character_relationship_pair" in relationship_constraints
    assert "unique_character_group_membership" in membership_constraints


def test_relationship_and_group_routes_are_named() -> None:
    character_id = uuid.uuid4()
    relationship_id = uuid.uuid4()
    group_id = uuid.uuid4()
    membership_id = uuid.uuid4()
    routes = {
        "character-relationship-create": {"character_id": character_id},
        "character-relationship-edit": {
            "character_id": character_id,
            "relationship_id": relationship_id,
        },
        "character-relationship-delete": {
            "character_id": character_id,
            "relationship_id": relationship_id,
        },
        "character-group-list": {},
        "character-group-create": {},
        "character-group-detail": {"group_id": group_id},
        "character-group-delete": {"group_id": group_id},
        "group-membership-create": {"group_id": group_id},
        "group-membership-edit": {
            "group_id": group_id,
            "membership_id": membership_id,
        },
        "group-membership-delete": {
            "group_id": group_id,
            "membership_id": membership_id,
        },
    }
    for name, kwargs in routes.items():
        assert resolve(reverse(name, kwargs=kwargs)).url_name == name


def test_connected_cast_templates_use_post_for_mutations_and_confirm_deletion() -> None:
    templates = Path(__file__).parents[1] / "templates/characters"
    relationship_delete = (templates / "relationship_delete.html").read_text()
    group_delete = (templates / "group_delete.html").read_text()
    group_detail = (templates / "group_detail.html").read_text()
    for template in (relationship_delete, group_delete, group_detail):
        assert 'method="post"' in template
        assert "{% csrf_token %}" in template
    assert "Delete relationship" in relationship_delete
    assert "Delete Group" in group_delete
    assert "Remove member" in group_detail


def test_groups_are_exposed_in_shared_navigation_and_combined_search() -> None:
    root = Path(__file__).parents[1] / "templates"
    for template in (
        root / "workspaces/home.html",
        root / "scenes/list.html",
        root / "characters/list.html",
        root / "characters/detail.html",
    ):
        content = template.read_text()
        assert "{% url 'character-group-list' %}" in content
    search = (root / "scenes/search.html").read_text()
    assert 'class="search-result-group-heading">Groups<' in search
    assert "character-group-detail" in search


def test_connected_cast_migration_remains_narrow_and_typed() -> None:
    migration = next(
        (Path(__file__).parents[1] / "src/characters/migrations").glob("0003_charactergroup_*.py")
    ).read_text()
    for model in ("CharacterGroup", "CharacterRelationship", "GroupMembership"):
        assert model in migration
    for forbidden in ("GenericForeignKey", "ContentType", "JSONField", "RunPython", "RunSQL"):
        assert forbidden not in migration


def test_connected_cast_styles_preserve_focus_overflow_and_narrow_layouts() -> None:
    css = (Path(__file__).parents[1] / "static/strange_novelty/app.css").read_text()
    assert ".group-card:focus-visible" in css
    assert ".character-group-row:focus-visible" in css
    assert "overflow-wrap: anywhere" in css
    assert "@media (max-width: 48rem)" in css
    narrow_rules = css.split("@media (max-width: 48rem)", maxsplit=1)[1]
    assert ".group-card-list" in narrow_rules
    assert ".relationship-card-heading" in narrow_rules
    assert ".membership-detail-grid" in narrow_rules
