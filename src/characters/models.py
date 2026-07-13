import uuid
from typing import cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from scenes.models import Scene
from workspaces.models import Workspace


class Character(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="characters")
    name = models.CharField(max_length=200)
    aliases = models.TextField(blank=True)
    role = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True)
    appearance = models.TextField(blank=True)
    personality = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    internal_conflict = models.TextField(blank=True)
    external_conflict = models.TextField(blank=True)
    voice_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    scenes = models.ManyToManyField(Scene, through="CharacterScene", related_name="characters")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"), name="character_name_contains_nonspace"
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "name"), name="character_ws_name_idx"),
            models.Index(fields=("workspace", "-updated_at"), name="character_ws_updated_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.name)

    @property
    def alias_list(self) -> tuple[str, ...]:
        return tuple(alias for line in self.aliases.splitlines() if (alias := line.strip()))

    @property
    def aliases_display(self) -> str:
        return ", ".join(self.alias_list)

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.name, str) or self.name != self.name.strip() or not self.name:
            raise ValidationError({"name": "Character name must be present and trimmed."})


class CharacterScene(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="character_scene_links"
    )
    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name="scene_links")
    scene = models.ForeignKey(Scene, on_delete=models.PROTECT, related_name="character_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("scene__ordering", "character__name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("character", "scene"), name="unique_character_scene_link"
            )
        ]
        indexes = [
            models.Index(fields=("workspace", "character"), name="char_scene_ws_char_idx"),
            models.Index(fields=("workspace", "scene"), name="char_scene_ws_scene_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.character} in {self.scene}"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.character_id and self.character.workspace_id != self.workspace_id:
            errors["character"] = "Character must belong to this Workspace."
        if self.scene_id and self.scene.workspace_id != self.workspace_id:
            errors["scene"] = "Scene must belong to this Workspace."
        if errors:
            raise ValidationError(errors)
