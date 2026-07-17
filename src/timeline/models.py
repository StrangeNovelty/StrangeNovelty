import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from workspaces.models import Workspace


def choices(values):
    return tuple((value, value.replace("_", " ").title()) for value in values)


class Timeline(models.Model):
    TYPES = choices(
        (
            "primary_story",
            "historical",
            "character",
            "faction",
            "location",
            "ability_progression",
            "publication",
            "alternate",
            "prophecy",
            "other",
        )
    )
    STATUSES = choices(("active", "draft", "archived"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="timelines")
    work = models.ForeignKey(
        "stories.Work", null=True, blank=True, on_delete=models.PROTECT, related_name="timelines"
    )
    name = models.CharField(max_length=240)
    timeline_type = models.CharField(max_length=32, choices=TYPES, default="primary_story")
    status = models.CharField(max_length=16, choices=STATUSES, default="draft")
    description = models.TextField(blank=True)
    calendar_system_label = models.CharField(max_length=160, blank=True)
    epoch_notes = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "name", "id")
        constraints = [
            models.UniqueConstraint(fields=("workspace", "name"), name="timeline_ws_name_uniq")
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.work_id and self.workspace_id and self.work.workspace_id != self.workspace_id:
            raise ValidationError({"work": "Work must belong to this Workspace."})


class TimelineEvent(models.Model):
    EVENT_TYPES = choices(
        (
            "story_event",
            "historical_event",
            "birth",
            "death",
            "disappearance",
            "discovery",
            "battle",
            "journey",
            "political_event",
            "relationship_event",
            "ability_event",
            "revelation",
            "secret_exposed",
            "clue_planted",
            "plot_thread_event",
            "location_event",
            "item_event",
            "creature_event",
            "cultural_event",
            "prophecy",
            "publication_event",
            "other",
        )
    )
    STATUSES = choices(("planned", "established", "disputed", "speculative", "deprecated"))
    PRECISIONS = choices(("exact", "approximate", "range", "relative", "unknown"))
    SIGNIFICANCE = choices(("major", "supporting", "minor", "background"))
    VISIBILITIES = choices(
        ("author_only", "reader_known", "character_known", "public_world", "secret", "disputed")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="timeline_events"
    )
    timeline = models.ForeignKey(Timeline, on_delete=models.CASCADE, related_name="events")
    work = models.ForeignKey(
        "stories.Work",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="timeline_events",
    )
    title = models.CharField(max_length=240)
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES, default="story_event")
    status = models.CharField(max_length=16, choices=STATUSES, default="planned")
    short_summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    chronology_precision = models.CharField(max_length=16, choices=PRECISIONS, default="unknown")
    start_sort_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    end_sort_value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    display_date = models.CharField(max_length=200, blank=True)
    end_label = models.CharField(max_length=200, blank=True)
    era_label = models.CharField(max_length=160, blank=True)
    uncertainty_notes = models.TextField(blank=True)
    significance = models.CharField(max_length=16, choices=SIGNIFICANCE, default="supporting")
    visibility = models.CharField(max_length=24, choices=VISIBILITIES, default="author_only")
    consequences = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = (models.F("start_sort_value").asc(nulls_last=True), "display_date", "id")
        indexes = [
            models.Index(
                fields=("workspace", "timeline", "start_sort_value"), name="event_ws_time_idx"
            )
        ]

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}
        if (
            self.timeline_id
            and self.workspace_id
            and self.timeline.workspace_id != self.workspace_id
        ):
            errors["timeline"] = "Timeline must belong to this Workspace."
        if self.work_id and self.workspace_id and self.work.workspace_id != self.workspace_id:
            errors["work"] = "Work must belong to this Workspace."
        if self.timeline_id and self.work_id and self.timeline.work_id not in (None, self.work_id):
            errors["work"] = "Work must match the Timeline's Work."
        if (
            self.end_sort_value is not None
            and self.start_sort_value is not None
            and self.end_sort_value < self.start_sort_value
        ):
            errors["end_sort_value"] = "End sort value cannot precede start sort value."
        if self.chronology_precision == "range" and self.end_sort_value is None:
            errors["end_sort_value"] = "Range Events require an end sort value."
        if errors:
            raise ValidationError(errors)


class EventTypedLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(TimelineEvent, on_delete=models.CASCADE)
    role = models.CharField(max_length=40, default="other")
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.event}: {self.role}"

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != "event":
                record = getattr(self, field.name, None)
                workspace_id = (
                    getattr(record, "workspace_id", None)
                    or getattr(getattr(record, "thread", None), "workspace_id", None)
                    or getattr(getattr(record, "draw", None), "workspace_id", None)
                    or getattr(getattr(record, "ability", None), "workspace_id", None)
                )
                if record and workspace_id != self.event.workspace_id:
                    raise ValidationError({field.name: "Link must belong to this Workspace."})
                work_id = getattr(record, "work_id", None) or getattr(
                    getattr(record, "thread", None), "work_id", None
                )
                if record and self.event.work_id and work_id and work_id != self.event.work_id:
                    raise ValidationError({field.name: "Link must belong to this Event's Work."})


def link_constraint(name, field):
    return [models.UniqueConstraint(fields=("event", field), name=name)]


class EventChapterLink(EventTypedLink):  # noqa: DJ008
    chapter = models.ForeignKey(
        "stories.Chapter", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_chapter_uniq", "chapter")


class EventWorkLink(EventTypedLink):  # noqa: DJ008
    work = models.ForeignKey(
        "stories.Work", on_delete=models.PROTECT, related_name="timeline_event_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_work_uniq", "work")


class EventVolumeLink(EventTypedLink):  # noqa: DJ008
    volume = models.ForeignKey(
        "stories.Volume", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_volume_uniq", "volume")


class EventArcLink(EventTypedLink):  # noqa: DJ008
    arc = models.ForeignKey("stories.Arc", on_delete=models.PROTECT, related_name="timeline_links")

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_arc_uniq", "arc")


class EventSceneLink(EventTypedLink):  # noqa: DJ008
    scene = models.ForeignKey(
        "scenes.Scene", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_scene_uniq", "scene")


class EventCharacterLink(EventTypedLink):  # noqa: DJ008
    character = models.ForeignKey(
        "characters.Character", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_character_uniq", "character")


class EventGroupLink(EventTypedLink):  # noqa: DJ008
    group = models.ForeignKey(
        "characters.CharacterGroup", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_group_uniq", "group")


class EventLocationLink(EventTypedLink):  # noqa: DJ008
    location = models.ForeignKey(
        "worldbuilding.Location", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_location_uniq", "location")


class EventRegionLink(EventTypedLink):  # noqa: DJ008
    region = models.ForeignKey(
        "worldbuilding.Region", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_region_uniq", "region")


class EventCodexLink(EventTypedLink):  # noqa: DJ008
    codex = models.ForeignKey(
        "worldbuilding.CodexEntry", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_codex_uniq", "codex")


class EventItemLink(EventTypedLink):  # noqa: DJ008
    item = models.ForeignKey(
        "worldbuilding.WorldItem", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_item_uniq", "item")


class EventCreatureLink(EventTypedLink):  # noqa: DJ008
    creature = models.ForeignKey(
        "worldbuilding.Creature", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_creature_uniq", "creature")


class EventThreadLink(EventTypedLink):  # noqa: DJ008
    thread = models.ForeignKey(
        "continuity.PlotThread", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_thread_uniq", "thread")


class EventSecretLink(EventTypedLink):  # noqa: DJ008
    secret = models.ForeignKey(
        "continuity.Secret", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_secret_uniq", "secret")


class EventClueLink(EventTypedLink):  # noqa: DJ008
    clue = models.ForeignKey(
        "continuity.ThreadClue", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_clue_uniq", "clue")


class EventRevealLink(EventTypedLink):  # noqa: DJ008
    reveal = models.ForeignKey(
        "continuity.ThreadReveal", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_reveal_uniq", "reveal")


class EventReaderKnowledgeLink(EventTypedLink):  # noqa: DJ008
    knowledge = models.ForeignKey(
        "continuity.ReaderKnowledgeRecord", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_reader_knowledge_uniq", "knowledge")


class EventCharacterKnowledgeLink(EventTypedLink):  # noqa: DJ008
    knowledge = models.ForeignKey(
        "continuity.CharacterKnowledgeRecord",
        on_delete=models.PROTECT,
        related_name="timeline_links",
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_character_knowledge_uniq", "knowledge")


class EventDrawLink(EventTypedLink):  # noqa: DJ008
    draw = models.ForeignKey(
        "decks.SavedDraw", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_draw_uniq", "draw")


class EventInterpretationLink(EventTypedLink):  # noqa: DJ008
    interpretation = models.ForeignKey(
        "decks.DrawInterpretation", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_interpretation_uniq", "interpretation")


class EventAbilityLink(EventTypedLink):  # noqa: DJ008
    ability = models.ForeignKey(
        "characters.Ability", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_ability_uniq", "ability")


class EventAbilityStageLink(EventTypedLink):  # noqa: DJ008
    stage = models.ForeignKey(
        "characters.AbilityStage", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_ability_stage_uniq", "stage")


class EventAbilityEventLink(EventTypedLink):  # noqa: DJ008
    ability_event = models.ForeignKey(
        "characters.AbilityEvent", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_ability_event_uniq", "ability_event")


class EventRelationshipLink(EventTypedLink):  # noqa: DJ008
    relationship = models.ForeignKey(
        "characters.CharacterRelationship", on_delete=models.PROTECT, related_name="timeline_links"
    )

    class Meta(EventTypedLink.Meta):
        constraints = link_constraint("event_relationship_uniq", "relationship")


class TimelineEventRelation(models.Model):
    TYPES = choices(
        (
            "before",
            "after",
            "simultaneous",
            "overlaps",
            "causes",
            "enables",
            "prevents",
            "contradicts",
            "retells",
            "flashback_to",
            "prophecy_of",
            "alternate_version",
            "other",
        )
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        TimelineEvent, on_delete=models.CASCADE, related_name="outgoing_relations"
    )
    target = models.ForeignKey(
        TimelineEvent, on_delete=models.CASCADE, related_name="incoming_relations"
    )
    relation_type = models.CharField(max_length=32, choices=TYPES)
    notes = models.TextField(blank=True)
    confidence = models.CharField(
        max_length=16, choices=choices(("high", "medium", "low")), default="high"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "target", "relation_type"), name="event_relation_uniq"
            ),
            models.CheckConstraint(
                condition=~Q(source=models.F("target")), name="event_relation_not_self"
            ),
        ]

    def __str__(self):
        return f"{self.source} {self.relation_type} {self.target}"

    def clean(self):
        if self.source_id == self.target_id:
            raise ValidationError({"target": "An Event cannot relate to itself."})
        if (
            self.source_id
            and self.target_id
            and self.source.workspace_id != self.target.workspace_id
        ):
            raise ValidationError({"target": "Events must belong to one Workspace."})
        if (
            self.relation_type == "simultaneous"
            and self.source.timeline_id != self.target.timeline_id
            and not self.notes.strip()
        ):
            raise ValidationError(
                {"notes": "Cross-Timeline simultaneous relations require a note."}
            )
