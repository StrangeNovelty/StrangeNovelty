import uuid
from typing import cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from characters.models import Character, CharacterGroup
from scenes.models import Scene
from stories.models import Chapter, Work
from workspaces.models import Workspace


class NamedWorldRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    aliases = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("name", "id")

    def __str__(self) -> str:
        return cast(str, self.name)

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.name, str) or self.name != self.name.strip() or not self.name:
            raise ValidationError({"name": "Name must be present and trimmed."})


class Region(NamedWorldRecord):
    class RegionType(models.TextChoices):
        CONTINENT = "continent", "Continent"
        COUNTRY = "country", "Country"
        TERRITORY = "territory", "Territory"
        PROVINCE = "province", "Province"
        ZONE = "zone", "Zone"
        DISTRICT = "district", "District"
        REALM = "realm", "Realm"
        PLANET = "planet", "Planet"
        SYSTEM = "system", "System"
        DIMENSION = "dimension", "Dimension"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        KNOWN = "known", "Known"
        UNKNOWN = "unknown", "Unknown"
        CONTESTED = "contested", "Contested"
        OCCUPIED = "occupied", "Occupied"
        DESTROYED = "destroyed", "Destroyed"
        INACCESSIBLE = "inaccessible", "Inaccessible"
        HISTORICAL = "historical", "Historical"

    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="regions")
    region_type = models.CharField(max_length=16, choices=RegionType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.KNOWN)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True)
    geography = models.TextField(blank=True)
    climate = models.TextField(blank=True)
    cultures = models.TextField(blank=True)
    government = models.TextField(blank=True)
    notable_features = models.TextField(blank=True)
    hazards = models.TextField(blank=True)

    def clean(self) -> None:
        super().clean()
        if self.parent_id:
            if self.parent_id == self.id:
                raise ValidationError({"parent": "A Region cannot parent itself."})
            if self.parent.workspace_id != self.workspace_id:
                raise ValidationError({"parent": "Parent Region must belong to this Workspace."})
            ancestor = self.parent
            seen = {self.id}
            while ancestor:
                if ancestor.id in seen:
                    raise ValidationError({"parent": "Region ancestry cannot contain a cycle."})
                seen.add(ancestor.id)
                ancestor = ancestor.parent


class Location(NamedWorldRecord):
    class LocationType(models.TextChoices):
        CITY = "city", "City"
        SETTLEMENT = "settlement", "Settlement"
        BUILDING = "building", "Building"
        LANDMARK = "landmark", "Landmark"
        WILDERNESS = "wilderness", "Wilderness"
        REALM = "realm", "Realm"
        PLANET = "planet", "Planet"
        STATION = "station", "Station"
        VESSEL = "vessel", "Vessel"
        BATTLEFIELD = "battlefield", "Battlefield"
        INTERIOR = "interior", "Interior"
        ABSTRACT = "abstract", "Abstract space"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ABANDONED = "abandoned", "Abandoned"
        RUINS = "ruins", "Ruins"
        DESTROYED = "destroyed", "Destroyed"
        HIDDEN = "hidden", "Hidden"
        INACCESSIBLE = "inaccessible", "Inaccessible"
        UNKNOWN = "unknown", "Unknown"
        HISTORICAL = "historical", "Historical"

    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="locations")
    location_type = models.CharField(max_length=16, choices=LocationType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    region = models.ForeignKey(
        Region, on_delete=models.PROTECT, null=True, blank=True, related_name="locations"
    )
    description = models.TextField(blank=True)
    history = models.TextField(blank=True)
    current_state = models.TextField(blank=True)
    atmosphere = models.TextField(blank=True)
    notable_features = models.TextField(blank=True)
    sensory_notes = models.TextField(blank=True)
    hazards = models.TextField(blank=True)
    culture = models.TextField(blank=True)
    travel_notes = models.TextField(blank=True)

    def clean(self) -> None:
        super().clean()
        if self.region_id and self.region.workspace_id != self.workspace_id:
            raise ValidationError({"region": "Region must belong to this Workspace."})


class CodexEntry(models.Model):
    class Category(models.TextChoices):
        CONCEPT = "concept", "Concept"
        HISTORY = "history", "History"
        BIOLOGY = "biology", "Biology"
        CULTURE = "culture", "Culture"
        TECHNOLOGY = "technology", "Technology"
        MAGIC = "magic", "Magic or power system"
        LANGUAGE = "language", "Language"
        LAW = "law", "Law"
        RELIGION = "religion", "Religion or belief"
        CUSTOM = "custom", "Custom"
        EVENT = "event", "Event"
        TERMINOLOGY = "terminology", "Terminology"
        OTHER = "other", "Other"

    class CanonState(models.TextChoices):
        CANON = "canon", "Canon"
        DRAFT = "draft", "Draft"
        SPECULATIVE = "speculative", "Speculative"
        DISPUTED = "disputed", "Disputed"
        DEPRECATED = "deprecated", "Deprecated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="codex_entries")
    term = models.CharField(max_length=200)
    aliases = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    status = models.CharField(max_length=120, blank=True)
    definition = models.TextField(blank=True)
    description = models.TextField(blank=True)
    implications = models.TextField(blank=True)
    related_terms = models.TextField(blank=True)
    canon_state = models.CharField(
        max_length=16, choices=CanonState.choices, default=CanonState.DRAFT
    )
    provenance_note = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("term", "id")

    def __str__(self) -> str:
        return cast(str, self.term)

    def clean(self) -> None:
        super().clean()
        if not self.term or self.term != self.term.strip():
            raise ValidationError({"term": "Term must be present and trimmed."})


class WorldItem(NamedWorldRecord):
    ITEM_TYPES = (
        (value, label)
        for value, label in (
            ("artifact", "Artifact"),
            ("weapon", "Weapon"),
            ("armor", "Armor"),
            ("tool", "Tool"),
            ("technology", "Technology"),
            ("vehicle", "Vehicle"),
            ("vessel", "Vessel"),
            ("document", "Document"),
            ("relic", "Relic"),
            ("substance", "Substance"),
            ("device", "Device"),
            ("key_item", "Key item"),
            ("ordinary", "Ordinary object"),
            ("other", "Other"),
        )
    )
    STATUSES = (
        (value, label)
        for value, label in (
            ("active", "Active"),
            ("lost", "Lost"),
            ("destroyed", "Destroyed"),
            ("damaged", "Damaged"),
            ("hidden", "Hidden"),
            ("sealed", "Sealed"),
            ("unknown", "Unknown"),
            ("historical", "Historical"),
        )
    )
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="world_items")
    item_type = models.CharField(max_length=16, choices=ITEM_TYPES)
    status = models.CharField(max_length=16, choices=STATUSES, default="active")
    significance = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    appearance = models.TextField(blank=True)
    origin = models.TextField(blank=True)
    function = models.TextField(blank=True)
    capabilities = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    costs_dangers = models.TextField(blank=True)
    current_condition = models.TextField(blank=True)
    current_location = models.ForeignKey(
        Location, on_delete=models.PROTECT, null=True, blank=True, related_name="current_items"
    )


class Creature(NamedWorldRecord):
    CREATURE_TYPES = (
        (value, label)
        for value, label in (
            ("individual", "Individual"),
            ("species", "Species"),
            ("monster", "Monster"),
            ("animal", "Animal"),
            ("construct", "Construct"),
            ("spirit", "Spirit"),
            ("entity", "Entity"),
            ("engineered", "Engineered organism"),
            ("alien", "Alien"),
            ("other", "Other"),
        )
    )
    STATUSES = (
        (value, label)
        for value, label in (
            ("active", "Active"),
            ("extinct", "Extinct"),
            ("dormant", "Dormant"),
            ("imprisoned", "Imprisoned"),
            ("missing", "Missing"),
            ("destroyed", "Destroyed"),
            ("unknown", "Unknown"),
            ("legendary", "Legendary"),
        )
    )
    THREATS = (
        (value, label)
        for value, label in (
            ("negligible", "Negligible"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
            ("severe", "Severe"),
            ("catastrophic", "Catastrophic"),
            ("unknown", "Unknown"),
        )
    )
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="creatures")
    creature_type = models.CharField(max_length=16, choices=CREATURE_TYPES)
    classification = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=16, choices=STATUSES, default="active")
    threat_level = models.CharField(max_length=16, choices=THREATS, default="unknown")
    intelligence = models.CharField(max_length=120, blank=True)
    appearance = models.TextField(blank=True)
    biology = models.TextField(blank=True)
    habitat = models.TextField(blank=True)
    behavior = models.TextField(blank=True)
    diet = models.TextField(blank=True)
    abilities = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    signs = models.TextField(blank=True)
    ecology = models.TextField(blank=True)
    origin = models.TextField(blank=True)
    cultural_significance = models.TextField(blank=True)
    encounter_notes = models.TextField(blank=True)


class TypedLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT)
    role = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        linked = [
            str(getattr(self, field.name))
            for field in self._meta.fields
            if isinstance(field, models.ForeignKey) and field.name != "workspace"
        ]
        return " — ".join(linked)

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != "workspace":
                value = getattr(self, field.name, None)
                if value is not None and getattr(value, "workspace_id", None) != self.workspace_id:
                    errors[field.name] = "Linked record must belong to this Workspace."
        if errors:
            raise ValidationError(errors)


def _link_model(
    name: str,
    left_name: str,
    left_model: type[models.Model],
    right_name: str,
    right_model: type[models.Model],
) -> type[models.Model]:
    meta = type(
        "Meta",
        (),
        {
            "constraints": [
                models.UniqueConstraint(
                    fields=(left_name, right_name), name=f"unique_{name.lower()}_pair"
                )
            ]
        },
    )
    attrs = {
        "__module__": __name__,
        left_name: models.ForeignKey(
            left_model, on_delete=models.PROTECT, related_name=f"{name.lower()}_links"
        ),
        right_name: models.ForeignKey(
            right_model, on_delete=models.PROTECT, related_name=f"{name.lower()}_links"
        ),
        "Meta": meta,
    }
    cls = type(name, (TypedLink,), attrs)
    globals()[name] = cls
    return cls


LocationCharacterLink = _link_model(
    "LocationCharacterLink", "location", Location, "character", Character
)
LocationGroupLink = _link_model("LocationGroupLink", "location", Location, "group", CharacterGroup)
RegionGroupLink = _link_model("RegionGroupLink", "region", Region, "group", CharacterGroup)
ItemCharacterLink = _link_model("ItemCharacterLink", "item", WorldItem, "character", Character)
ItemGroupLink = _link_model("ItemGroupLink", "item", WorldItem, "group", CharacterGroup)
CreatureCharacterLink = _link_model(
    "CreatureCharacterLink", "creature", Creature, "character", Character
)
CreatureGroupLink = _link_model("CreatureGroupLink", "creature", Creature, "group", CharacterGroup)
CreatureLocationLink = _link_model(
    "CreatureLocationLink", "creature", Creature, "location", Location
)
CreatureRegionLink = _link_model("CreatureRegionLink", "creature", Creature, "region", Region)
CreatureCodexLink = _link_model("CreatureCodexLink", "creature", Creature, "codex", CodexEntry)
SceneLocationLink = _link_model("SceneLocationLink", "scene", Scene, "location", Location)
SceneRegionLink = _link_model("SceneRegionLink", "scene", Scene, "region", Region)
SceneGroupLink = _link_model("SceneGroupLink", "scene", Scene, "group", CharacterGroup)
SceneCodexLink = _link_model("SceneCodexLink", "scene", Scene, "codex", CodexEntry)
SceneItemLink = _link_model("SceneItemLink", "scene", Scene, "item", WorldItem)
SceneCreatureLink = _link_model("SceneCreatureLink", "scene", Scene, "creature", Creature)
CodexCharacterLink = _link_model("CodexCharacterLink", "codex", CodexEntry, "character", Character)
CodexGroupLink = _link_model("CodexGroupLink", "codex", CodexEntry, "group", CharacterGroup)
CodexLocationLink = _link_model("CodexLocationLink", "codex", CodexEntry, "location", Location)
CodexRegionLink = _link_model("CodexRegionLink", "codex", CodexEntry, "region", Region)
CodexWorkLink = _link_model("CodexWorkLink", "codex", CodexEntry, "work", Work)
CodexChapterLink = _link_model("CodexChapterLink", "codex", CodexEntry, "chapter", Chapter)
CodexItemLink = _link_model("CodexItemLink", "codex", CodexEntry, "item", WorldItem)


class CodexRelation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="codex_relations"
    )
    source = models.ForeignKey(
        CodexEntry, on_delete=models.PROTECT, related_name="relations_as_source"
    )
    target = models.ForeignKey(
        CodexEntry, on_delete=models.PROTECT, related_name="relations_as_target"
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(source_id__lt=F("target_id")), name="codex_rel_pair_order"
            ),
            models.UniqueConstraint(fields=("source", "target"), name="unique_codex_rel_pair"),
        ]

    def __str__(self) -> str:
        return f"{self.source} — {self.target}"
