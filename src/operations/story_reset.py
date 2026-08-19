import uuid
from collections import deque
from dataclasses import dataclass
from enum import StrEnum

from django.apps import apps
from django.db import models

from workspaces.models import Workspace


class StoryResetInventoryError(RuntimeError):
    """Raised when a complete, workspace-scoped inventory cannot be produced."""


class ResetAction(StrEnum):
    REMOVE = "remove"
    REVIEW = "review"
    PRESERVE = "preserve"


PROJECT_APP_LABELS = frozenset(
    {
        "accounts",
        "ai_assistance",
        "characters",
        "continuity",
        "decks",
        "jobs",
        "legacy_imports",
        "library",
        "publishing",
        "scenes",
        "security_events",
        "stories",
        "timeline",
        "workspaces",
        "worldbuilding",
    }
)

REMOVE_APP_LABELS = frozenset(
    {
        "ai_assistance",
        "characters",
        "continuity",
        "legacy_imports",
        "publishing",
        "scenes",
        "stories",
        "timeline",
        "worldbuilding",
    }
)

PRESERVE_APP_LABELS = frozenset({"accounts", "security_events", "workspaces"})
REVIEW_APP_LABELS = frozenset({"jobs", "library"})

DECK_STORY_ACTIVITY_MODELS = frozenset(
    {
        "DrawCard",
        "DrawCardHistory",
        "DrawCharacterContext",
        "DrawCodexContext",
        "DrawConversion",
        "DrawCreatureContext",
        "DrawDeckSelection",
        "DrawGroupContext",
        "DrawInterpretation",
        "DrawItemContext",
        "DrawLocationContext",
        "DrawRegionContext",
        "SavedDraw",
    }
)

LIBRARY_STORY_LINK_MODELS = frozenset({"LibraryConnection"})


@dataclass(frozen=True)
class InventorySpec:
    model: type[models.Model]
    action: ResetAction
    workspace_lookup: str | None

    @property
    def label(self) -> str:
        return self.model._meta.label


@dataclass(frozen=True)
class InventoryRow:
    label: str
    action: ResetAction
    count: int | None
    workspace_lookup: str | None


@dataclass(frozen=True)
class StoryResetInventory:
    workspace_id: uuid.UUID
    rows: tuple[InventoryRow, ...]

    def rows_for(self, action: ResetAction) -> tuple[InventoryRow, ...]:
        return tuple(row for row in self.rows if row.action == action)

    def total_for(self, action: ResetAction) -> int:
        return sum(row.count or 0 for row in self.rows_for(action))

    def as_dict(self) -> dict[str, object]:
        actions: dict[str, list[dict[str, object]]] = {}
        totals: dict[str, int] = {}
        for action in ResetAction:
            rows = self.rows_for(action)
            totals[action.value] = self.total_for(action)
            actions[action.value] = [
                {
                    "model": row.label,
                    "count": row.count,
                    "workspace_scoped": row.workspace_lookup is not None,
                }
                for row in rows
            ]
        return {
            "mode": "read-only",
            "workspace": str(self.workspace_id),
            "totals": totals,
            "actions": actions,
        }


def reset_action_for_model(model: type[models.Model]) -> ResetAction:
    app_label = model._meta.app_label
    model_name = model.__name__
    if app_label in REMOVE_APP_LABELS:
        return ResetAction.REMOVE
    if app_label == "decks":
        if model_name in DECK_STORY_ACTIVITY_MODELS:
            return ResetAction.REMOVE
        return ResetAction.PRESERVE
    if app_label == "library" and model_name in LIBRARY_STORY_LINK_MODELS:
        return ResetAction.REMOVE
    if app_label in REVIEW_APP_LABELS:
        return ResetAction.REVIEW
    if app_label in PRESERVE_APP_LABELS:
        return ResetAction.PRESERVE
    raise StoryResetInventoryError(f"Unclassified project model: {model._meta.label}.")


def _workspace_lookup(model: type[models.Model]) -> str | None:
    if model is Workspace:
        return "id"
    queue: deque[tuple[type[models.Model], tuple[str, ...]]] = deque([(model, ())])
    visited: set[type[models.Model]] = {model}
    while queue:
        current, path = queue.popleft()
        relation_fields = sorted(
            (
                field
                for field in current._meta.fields
                if field.is_relation and (field.many_to_one or field.one_to_one)
            ),
            key=lambda field: field.name,
        )
        for field in relation_fields:
            related = field.related_model
            if not isinstance(related, type) or not issubclass(related, models.Model):
                continue
            next_path = (*path, field.name)
            if related is Workspace:
                return "__".join((*next_path, "id"))
            if related._meta.app_label not in PROJECT_APP_LABELS or related in visited:
                continue
            visited.add(related)
            queue.append((related, next_path))
    return None


def story_reset_inventory_specs() -> tuple[InventorySpec, ...]:
    specs: list[InventorySpec] = []
    for model in apps.get_models():
        if model._meta.app_label not in PROJECT_APP_LABELS or model._meta.proxy:
            continue
        action = reset_action_for_model(model)
        lookup = _workspace_lookup(model)
        if action != ResetAction.PRESERVE and lookup is None:
            raise StoryResetInventoryError(
                f"{model._meta.label} is {action.value} but has no safe Workspace scope."
            )
        specs.append(InventorySpec(model=model, action=action, workspace_lookup=lookup))
    return tuple(sorted(specs, key=lambda spec: (spec.action.value, spec.label)))


def inspect_story_reset(workspace_id: uuid.UUID) -> StoryResetInventory:
    if not Workspace.objects.filter(id=workspace_id).exists():
        raise StoryResetInventoryError("Workspace does not exist.")
    rows: list[InventoryRow] = []
    for spec in story_reset_inventory_specs():
        count = None
        if spec.workspace_lookup is not None:
            count = spec.model._default_manager.filter(
                **{spec.workspace_lookup: workspace_id}
            ).count()
        rows.append(
            InventoryRow(
                label=spec.label,
                action=spec.action,
                count=count,
                workspace_lookup=spec.workspace_lookup,
            )
        )
    return StoryResetInventory(workspace_id=workspace_id, rows=tuple(rows))
