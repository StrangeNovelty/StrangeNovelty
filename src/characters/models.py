import uuid
from typing import cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

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


class CharacterRelationship(models.Model):
    class RelationshipType(models.TextChoices):
        FAMILY = "family", "Family"
        ALLY = "ally", "Ally"
        FRIEND = "friend", "Friend"
        RIVAL = "rival", "Rival"
        ENEMY = "enemy", "Enemy"
        ROMANTIC = "romantic", "Romantic"
        MENTOR = "mentor", "Mentor"
        STUDENT = "student", "Student"
        EMPLOYER = "employer", "Employer"
        SUBORDINATE = "subordinate", "Subordinate"
        PROFESSIONAL = "professional", "Professional"
        DEPENDENT = "dependent", "Dependent"
        COMPLICATED = "complicated", "Complicated"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        STRAINED = "strained", "Strained"
        BROKEN = "broken", "Broken"
        HIDDEN = "hidden", "Hidden"
        RESOLVED = "resolved", "Resolved"
        HISTORICAL = "historical", "Historical"

    class KnowledgeState(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        SECRET = "secret", "Secret"
        ONE_SIDED = "one_sided", "One-sided"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="character_relationships"
    )
    source = models.ForeignKey(
        Character, on_delete=models.PROTECT, related_name="relationships_as_source"
    )
    target = models.ForeignKey(
        Character, on_delete=models.PROTECT, related_name="relationships_as_target"
    )
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices)
    short_label = models.CharField(max_length=160, blank=True)
    summary = models.TextField(blank=True)
    source_perspective = models.TextField(blank=True)
    target_perspective = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    knowledge_state = models.CharField(
        max_length=16,
        choices=KnowledgeState.choices,
        default=KnowledgeState.PRIVATE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(source_id__lt=F("target_id")),
                name="relationship_pair_canonical",
            ),
            models.CheckConstraint(
                condition=Q(
                    relationship_type__in=(
                        "family",
                        "ally",
                        "friend",
                        "rival",
                        "enemy",
                        "romantic",
                        "mentor",
                        "student",
                        "employer",
                        "subordinate",
                        "professional",
                        "dependent",
                        "complicated",
                        "other",
                    )
                ),
                name="relationship_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "active",
                        "strained",
                        "broken",
                        "hidden",
                        "resolved",
                        "historical",
                    )
                ),
                name="relationship_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(
                    knowledge_state__in=(
                        "public",
                        "private",
                        "secret",
                        "one_sided",
                        "unknown",
                    )
                ),
                name="relationship_knowledge_valid",
            ),
            models.UniqueConstraint(
                fields=("source", "target"),
                name="unique_character_relationship_pair",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "source"), name="relationship_ws_source_idx"),
            models.Index(fields=("workspace", "target"), name="relationship_ws_target_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source} — {self.target}"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.workspace_id and self.source_id and self.source.workspace_id != self.workspace_id:
            errors["source"] = "Source Character must belong to this Workspace."
        if self.workspace_id and self.target_id and self.target.workspace_id != self.workspace_id:
            errors["target"] = "Target Character must belong to this Workspace."
        if self.source_id and self.target_id and self.source_id >= self.target_id:
            errors["target"] = "Relationship pair must use canonical Character order."
        if errors:
            raise ValidationError(errors)


class CharacterGroup(models.Model):
    class Alignment(models.TextChoices):
        ALLIED = "allied", "Allied"
        FRIENDLY = "friendly", "Friendly"
        NEUTRAL = "neutral", "Neutral"
        HOSTILE = "hostile", "Hostile"
        MIXED = "mixed", "Mixed"
        UNKNOWN = "unknown", "Unknown"

    class GroupType(models.TextChoices):
        FAMILY = "family", "Family"
        TEAM = "team", "Team"
        FACTION = "faction", "Faction"
        ORGANIZATION = "organization", "Organization"
        CREW = "crew", "Crew"
        HOUSEHOLD = "household", "Household"
        ORDER = "order", "Order"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DISSOLVED = "dissolved", "Dissolved"
        HISTORICAL = "historical", "Historical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="character_groups"
    )
    name = models.CharField(max_length=200)
    group_type = models.CharField(max_length=20, choices=GroupType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    tagline = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    purpose = models.TextField(blank=True)
    alignment = models.CharField(
        max_length=16, choices=Alignment.choices, default=Alignment.UNKNOWN
    )
    public_goals = models.TextField(blank=True)
    hidden_goals = models.TextField(blank=True)
    resources = models.TextField(blank=True)
    territory = models.TextField(blank=True)
    leadership_notes = models.TextField(blank=True)
    methods = models.TextField(blank=True)
    reputation = models.TextField(blank=True)
    allies = models.TextField(blank=True)
    enemies = models.TextField(blank=True)
    current_conflicts = models.TextField(blank=True)
    history = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"), name="character_group_name_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(
                    group_type__in=(
                        "family",
                        "team",
                        "faction",
                        "organization",
                        "crew",
                        "household",
                        "order",
                        "other",
                    )
                ),
                name="character_group_type_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("active", "inactive", "dissolved", "historical")),
                name="character_group_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "name"), name="character_group_ws_name_idx"),
            models.Index(
                fields=("workspace", "-updated_at"), name="character_group_ws_updated_idx"
            ),
        ]

    def __str__(self) -> str:
        return cast(str, self.name)

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.name, str) or self.name != self.name.strip() or not self.name:
            raise ValidationError({"name": "Group name must be present and trimmed."})


class GroupRelationship(models.Model):
    class RelationshipType(models.TextChoices):
        ALLIED = "allied", "Allied"
        HOSTILE = "hostile", "Hostile"
        SUBORDINATE = "subordinate", "Subordinate"
        RIVAL = "rival", "Rival"
        TRADING_PARTNER = "trading_partner", "Trading partner"
        CEASEFIRE = "ceasefire", "Ceasefire"
        SECRET_COLLABORATION = "secret_collaboration", "Secret collaboration"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="group_relationships"
    )
    source = models.ForeignKey(
        CharacterGroup, on_delete=models.PROTECT, related_name="relationships_as_source"
    )
    target = models.ForeignKey(
        CharacterGroup, on_delete=models.PROTECT, related_name="relationships_as_target"
    )
    relationship_type = models.CharField(max_length=24, choices=RelationshipType.choices)
    summary = models.TextField(blank=True)
    source_perspective = models.TextField(blank=True)
    target_perspective = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(source_id__lt=F("target_id")), name="group_rel_pair_order"
            ),
            models.UniqueConstraint(fields=("source", "target"), name="unique_group_rel_pair"),
        ]

    def __str__(self) -> str:
        return f"{self.source} — {self.target}"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.source_id and self.source.workspace_id != self.workspace_id:
            errors["source"] = "Source Group must belong to this Workspace."
        if self.target_id and self.target.workspace_id != self.workspace_id:
            errors["target"] = "Target Group must belong to this Workspace."
        if self.source_id and self.target_id and self.source_id >= self.target_id:
            errors["target"] = "Group relationship pair must use canonical order."
        if errors:
            raise ValidationError(errors)


class GroupMembership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FORMER = "former", "Former"
        HIDDEN = "hidden", "Hidden"
        HONORARY = "honorary", "Honorary"
        DECEASED = "deceased", "Deceased"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="group_memberships"
    )
    character = models.ForeignKey(
        Character, on_delete=models.PROTECT, related_name="group_memberships"
    )
    group = models.ForeignKey(CharacterGroup, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    rank_label = models.CharField(max_length=120, blank=True)
    joined_story_time = models.CharField(max_length=120, blank=True)
    left_story_time = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("character__name", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=(
                        "active",
                        "former",
                        "hidden",
                        "honorary",
                        "deceased",
                        "unknown",
                    )
                ),
                name="group_membership_status_valid",
            ),
            models.UniqueConstraint(
                fields=("character", "group"),
                name="unique_character_group_membership",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "character"), name="membership_ws_char_idx"),
            models.Index(fields=("workspace", "group"), name="membership_ws_group_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.character} in {self.group}"

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if (
            self.workspace_id
            and self.character_id
            and self.character.workspace_id != self.workspace_id
        ):
            errors["character"] = "Membership Character must belong to this Workspace."
        if self.workspace_id and self.group_id and self.group.workspace_id != self.workspace_id:
            errors["group"] = "Membership Group must belong to this Workspace."
        if errors:
            raise ValidationError(errors)


class Ability(models.Model):
    class Mastery(models.TextChoices):
        LATENT = "latent", "Latent"
        EMERGING = "emerging", "Emerging"
        TRAINED = "trained", "Trained"
        ADVANCED = "advanced", "Advanced"
        MASTERED = "mastered", "Mastered"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DORMANT = "dormant", "Dormant"
        LOST = "lost", "Lost"
        UNSTABLE = "unstable", "Unstable"
        SEALED = "sealed", "Sealed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="abilities")
    character = models.ForeignKey(Character, on_delete=models.PROTECT, related_name="abilities")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    costs = models.TextField(blank=True)
    mastery = models.CharField(max_length=16, choices=Mastery.choices, default=Mastery.EMERGING)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"), name="ability_name_contains_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(mastery__in=("latent", "emerging", "trained", "advanced", "mastered")),
                name="ability_mastery_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("active", "dormant", "lost", "unstable", "sealed")),
                name="ability_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "character"), name="ability_ws_character_idx"),
            models.Index(fields=("workspace", "-updated_at"), name="ability_ws_updated_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.name)

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.character_id and self.character.workspace_id != self.workspace_id:
            errors["character"] = "Ability Character must belong to this Workspace."
        if not isinstance(self.name, str) or self.name != self.name.strip() or not self.name:
            errors["name"] = "Ability name must be present and trimmed."
        if errors:
            raise ValidationError(errors)


class AbilityStage(models.Model):
    class State(models.TextChoices):
        PAST = "past", "Past"
        CURRENT = "current", "Current"
        POSSIBLE = "possible", "Possible"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ability_stages"
    )
    ability = models.ForeignKey(Ability, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=16, choices=State.choices, default=State.POSSIBLE)
    requirements = models.TextField(blank=True)
    costs = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(name__regex=r"\S"), name="ability_stage_name_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(state__in=("past", "current", "possible", "rejected")),
                name="ability_stage_state_valid",
            ),
            models.UniqueConstraint(fields=("ability", "order"), name="unique_ability_stage_order"),
            models.UniqueConstraint(
                fields=("ability",),
                condition=Q(state="current"),
                name="unique_current_stage_per_ability",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "ability"), name="stage_ws_ability_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.name)

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.workspace_id and self.ability_id and self.ability.workspace_id != self.workspace_id:
            errors["ability"] = "Ability Stage must belong to this Workspace."
        if not isinstance(self.name, str) or self.name != self.name.strip() or not self.name:
            errors["name"] = "Stage name must be present and trimmed."
        if errors:
            raise ValidationError(errors)


class AbilityEvent(models.Model):
    class EventType(models.TextChoices):
        AWAKENING = "awakening", "Awakening"
        TRAINING = "training", "Training"
        BREAKTHROUGH = "breakthrough", "Breakthrough"
        FAILURE = "failure", "Failure"
        INJURY = "injury", "Injury"
        LOSS = "loss", "Loss"
        DISCOVERY = "discovery", "Discovery"
        TRANSFORMATION = "transformation", "Transformation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ability_events"
    )
    ability = models.ForeignKey(Ability, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=200)
    event_date = models.DateField(null=True, blank=True)
    story_time = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.DISCOVERY
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ability_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="ability_event_title_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(
                    event_type__in=(
                        "awakening",
                        "training",
                        "breakthrough",
                        "failure",
                        "injury",
                        "loss",
                        "discovery",
                        "transformation",
                    )
                ),
                name="ability_event_type_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "ability"), name="event_ws_ability_idx"),
            models.Index(fields=("workspace", "-created_at"), name="event_ws_created_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.workspace_id and self.ability_id and self.ability.workspace_id != self.workspace_id:
            errors["ability"] = "Ability Event must belong to this Workspace."
        if self.workspace_id and self.scene_id and self.scene.workspace_id != self.workspace_id:
            errors["scene"] = "Linked Scene must belong to this Workspace."
        if not isinstance(self.title, str) or self.title != self.title.strip() or not self.title:
            errors["title"] = "Event title must be present and trimmed."
        if errors:
            raise ValidationError(errors)


class AbilityPrediction(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CAME_TRUE = "came_true", "Came true"
        DIVERGED = "diverged", "Diverged"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="ability_predictions"
    )
    ability = models.ForeignKey(Ability, on_delete=models.CASCADE, related_name="predictions")
    title = models.CharField(max_length=200)
    prediction = models.TextField()
    rationale = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(title__regex=r"\S"), name="ability_prediction_title_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(prediction__regex=r"\S"), name="ability_prediction_nonspace"
            ),
            models.CheckConstraint(
                condition=Q(status__in=("active", "came_true", "diverged", "dismissed")),
                name="ability_prediction_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("workspace", "ability"), name="prediction_ws_ability_idx"),
        ]

    def __str__(self) -> str:
        return cast(str, self.title)

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        if self.workspace_id and self.ability_id and self.ability.workspace_id != self.workspace_id:
            errors["ability"] = "Ability Prediction must belong to this Workspace."
        if not isinstance(self.title, str) or self.title != self.title.strip() or not self.title:
            errors["title"] = "Prediction title must be present and trimmed."
        if (
            not isinstance(self.prediction, str)
            or self.prediction != self.prediction.strip()
            or not self.prediction
        ):
            errors["prediction"] = "Prediction must be present and trimmed."
        if errors:
            raise ValidationError(errors)
