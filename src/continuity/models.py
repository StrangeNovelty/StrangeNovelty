import uuid

from django.core.exceptions import ValidationError
from django.db import models

from workspaces.models import Workspace


class PlotThread(models.Model):
    TYPES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "foreshadowing",
            "mystery",
            "promise",
            "threat",
            "callback",
            "motif",
            "character_arc",
            "relationship_arc",
            "world_arc",
            "political_arc",
            "object_arc",
            "location_arc",
            "prophecy",
            "question",
            "setup",
            "other",
        )
    )
    STATUSES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "planned",
            "open",
            "developing",
            "dormant",
            "endangered",
            "resolved",
            "abandoned",
            "superseded",
        )
    )
    PRIORITIES = tuple((v, v.title()) for v in ("critical", "high", "medium", "low", "background"))
    VISIBILITIES = tuple(
        (v, v.replace("_", " ").title())
        for v in (
            "author_only",
            "reader_aware",
            "character_aware",
            "public_world",
            "hidden",
            "disputed",
        )
    )
    HEALTH = tuple(
        (v, v.title()) for v in ("healthy", "watch", "endangered", "blocked", "resolved")
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="plot_threads")
    work = models.ForeignKey(
        "stories.Work", null=True, blank=True, on_delete=models.PROTECT, related_name="plot_threads"
    )
    volume = models.ForeignKey(
        "stories.Volume",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="plot_threads",
    )
    arc = models.ForeignKey(
        "stories.Arc", null=True, blank=True, on_delete=models.PROTECT, related_name="plot_threads"
    )
    title = models.CharField(max_length=240)
    thread_type = models.CharField(max_length=32, choices=TYPES, default="other")
    status = models.CharField(max_length=20, choices=STATUSES, default="planned")
    priority = models.CharField(max_length=16, choices=PRIORITIES, default="medium")
    visibility = models.CharField(max_length=24, choices=VISIBILITIES, default="author_only")
    health = models.CharField(max_length=16, choices=HEALTH, default="healthy")
    short_summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    intended_payoff = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)
    introduced_story_time = models.CharField(max_length=160, blank=True)
    target_resolution_story_time = models.CharField(max_length=160, blank=True)
    resolved_story_time = models.CharField(max_length=160, blank=True)
    next_action = models.TextField(blank=True)
    next_review_label = models.CharField(max_length=160, blank=True)
    blocker_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        indexes = [
            models.Index(fields=("workspace", "status", "priority"), name="thread_ws_status_idx")
        ]

    def __str__(self):
        return self.title

    def clean(self):
        for name in ("work", "volume", "arc"):
            value = getattr(self, name, None)
            if value and self.workspace_id and value.workspace_id != self.workspace_id:
                raise ValidationError({name: "Selection must belong to this Workspace."})
            if value and self.work_id and getattr(value, "work_id", self.work_id) != self.work_id:
                raise ValidationError({name: "Selection must belong to this Work."})


class ThreadTypedLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(PlotThread, on_delete=models.CASCADE)
    role = models.CharField(max_length=40, default="other")
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.thread}: {self.role}"

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != "thread":
                record = getattr(self, field.name, None)
                if record and record.workspace_id != self.thread.workspace_id:
                    raise ValidationError({field.name: "Link must belong to this Workspace."})
                work_id = getattr(record, "work_id", None)
                if record and self.thread.work_id and work_id and work_id != self.thread.work_id:
                    raise ValidationError({field.name: "Link must belong to this Thread's Work."})


def _link_meta(name, field):
    return [models.UniqueConstraint(fields=("thread", field), name=name)]


class ThreadChapterLink(ThreadTypedLink):  # noqa: DJ008
    chapter = models.ForeignKey(
        "stories.Chapter", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_chapter_uniq", "chapter")


class ThreadSceneLink(ThreadTypedLink):  # noqa: DJ008
    scene = models.ForeignKey("scenes.Scene", on_delete=models.PROTECT, related_name="thread_links")

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_scene_uniq", "scene")


class ThreadCharacterLink(ThreadTypedLink):  # noqa: DJ008
    character = models.ForeignKey(
        "characters.Character", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_character_uniq", "character")


class ThreadGroupLink(ThreadTypedLink):  # noqa: DJ008
    group = models.ForeignKey(
        "characters.CharacterGroup", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_group_uniq", "group")


class ThreadLocationLink(ThreadTypedLink):  # noqa: DJ008
    location = models.ForeignKey(
        "worldbuilding.Location", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_location_uniq", "location")


class ThreadRegionLink(ThreadTypedLink):  # noqa: DJ008
    region = models.ForeignKey(
        "worldbuilding.Region", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_region_uniq", "region")


class ThreadCodexLink(ThreadTypedLink):  # noqa: DJ008
    codex = models.ForeignKey(
        "worldbuilding.CodexEntry", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_codex_uniq", "codex")


class ThreadItemLink(ThreadTypedLink):  # noqa: DJ008
    item = models.ForeignKey(
        "worldbuilding.WorldItem", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_item_uniq", "item")


class ThreadCreatureLink(ThreadTypedLink):  # noqa: DJ008
    creature = models.ForeignKey(
        "worldbuilding.Creature", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_creature_uniq", "creature")


class ThreadDrawLink(ThreadTypedLink):  # noqa: DJ008
    draw = models.ForeignKey(
        "decks.SavedDraw", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_draw_uniq", "draw")


class ThreadInterpretationLink(ThreadTypedLink):  # noqa: DJ008
    interpretation = models.ForeignKey(
        "decks.DrawInterpretation", on_delete=models.PROTECT, related_name="thread_links"
    )

    class Meta(ThreadTypedLink.Meta):
        constraints = _link_meta("thread_interp_uniq", "interpretation")


class ThreadProgressEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(PlotThread, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=32, default="other")
    title = models.CharField(max_length=240)
    story_time_label = models.CharField(max_length=160, blank=True)
    calendar_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    chapter = models.ForeignKey("stories.Chapter", null=True, blank=True, on_delete=models.PROTECT)
    scene = models.ForeignKey("scenes.Scene", null=True, blank=True, on_delete=models.PROTECT)
    status_impact = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "id")

    def __str__(self):
        return self.title


class ThreadClue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(PlotThread, on_delete=models.CASCADE, related_name="clues")
    clue_type = models.CharField(max_length=32, default="direct_clue")
    title = models.CharField(max_length=240)
    description = models.TextField()
    status = models.CharField(max_length=20, default="planned")
    subtlety = models.CharField(max_length=20, default="subtle")
    chapter = models.ForeignKey(
        "stories.Chapter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="thread_clues",
    )
    scene = models.ForeignKey(
        "scenes.Scene", null=True, blank=True, on_delete=models.PROTECT, related_name="thread_clues"
    )
    intended_interpretation = models.TextField(blank=True)
    reader_interpretation_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ThreadReveal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(PlotThread, on_delete=models.CASCADE, related_name="reveals")
    title = models.CharField(max_length=240)
    reveal_type = models.CharField(max_length=32, default="partial")
    description = models.TextField()
    status = models.CharField(max_length=20, default="planned")
    chapter = models.ForeignKey(
        "stories.Chapter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="thread_reveals",
    )
    scene = models.ForeignKey(
        "scenes.Scene",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="thread_reveals",
    )
    target_audience = models.CharField(max_length=240, blank=True)
    consequences = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Secret(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="secrets")
    work = models.ForeignKey(
        "stories.Work", null=True, blank=True, on_delete=models.PROTECT, related_name="secrets"
    )
    thread = models.ForeignKey(
        PlotThread, null=True, blank=True, on_delete=models.PROTECT, related_name="secrets"
    )
    title = models.CharField(max_length=240)
    secret_type = models.CharField(max_length=32, default="other")
    status = models.CharField(max_length=24, default="hidden")
    truth_statement = models.TextField()
    public_belief = models.TextField(blank=True)
    why_it_matters = models.TextField(blank=True)
    consequences_if_revealed = models.TextField(blank=True)
    intended_reveal = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def clean(self):
        for name in ("work", "thread"):
            value = getattr(self, name, None)
            if value and self.workspace_id and value.workspace_id != self.workspace_id:
                raise ValidationError({name: "Selection must belong to this Workspace."})
        if self.thread_id and self.work_id and self.thread.work_id not in (None, self.work_id):
            raise ValidationError({"thread": "Thread must belong to this Work."})


class SecretTypedLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE)
    role = models.CharField(max_length=40, default="subject")
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.secret}: {self.role}"

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != "secret":
                record = getattr(self, field.name, None)
                if record and record.workspace_id != self.secret.workspace_id:
                    raise ValidationError({field.name: "Link must belong to this Workspace."})
                work_id = getattr(record, "work_id", None)
                if record and self.secret.work_id and work_id and work_id != self.secret.work_id:
                    raise ValidationError({field.name: "Link must belong to this Secret's Work."})


def _secret_link(name, field):
    return [models.UniqueConstraint(fields=("secret", field), name=name)]


class SecretCharacterLink(SecretTypedLink):  # noqa: DJ008
    character = models.ForeignKey(
        "characters.Character", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_character_uniq", "character")


class SecretGroupLink(SecretTypedLink):  # noqa: DJ008
    group = models.ForeignKey(
        "characters.CharacterGroup", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_group_uniq", "group")


class SecretLocationLink(SecretTypedLink):  # noqa: DJ008
    location = models.ForeignKey(
        "worldbuilding.Location", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_location_uniq", "location")


class SecretRegionLink(SecretTypedLink):  # noqa: DJ008
    region = models.ForeignKey(
        "worldbuilding.Region", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_region_uniq", "region")


class SecretCodexLink(SecretTypedLink):  # noqa: DJ008
    codex = models.ForeignKey(
        "worldbuilding.CodexEntry", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_codex_uniq", "codex")


class SecretItemLink(SecretTypedLink):  # noqa: DJ008
    item = models.ForeignKey(
        "worldbuilding.WorldItem", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_item_uniq", "item")


class SecretCreatureLink(SecretTypedLink):  # noqa: DJ008
    creature = models.ForeignKey(
        "worldbuilding.Creature", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_creature_uniq", "creature")


class SecretChapterLink(SecretTypedLink):  # noqa: DJ008
    chapter = models.ForeignKey(
        "stories.Chapter", on_delete=models.PROTECT, related_name="secret_links"
    )

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_chapter_uniq", "chapter")


class SecretSceneLink(SecretTypedLink):  # noqa: DJ008
    scene = models.ForeignKey("scenes.Scene", on_delete=models.PROTECT, related_name="secret_links")

    class Meta(SecretTypedLink.Meta):
        constraints = _secret_link("secret_scene_uniq", "scene")


class KnowledgeSubject(models.Model):
    secret = models.ForeignKey(Secret, null=True, blank=True, on_delete=models.PROTECT)
    thread = models.ForeignKey(PlotThread, null=True, blank=True, on_delete=models.PROTECT)
    character_subject = models.ForeignKey(
        "characters.Character", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    group_subject = models.ForeignKey(
        "characters.CharacterGroup",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    location = models.ForeignKey(
        "worldbuilding.Location", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    region = models.ForeignKey(
        "worldbuilding.Region", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    codex = models.ForeignKey(
        "worldbuilding.CodexEntry",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    item = models.ForeignKey(
        "worldbuilding.WorldItem", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    creature = models.ForeignKey(
        "worldbuilding.Creature", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        abstract = True


class ReaderKnowledgeRecord(KnowledgeSubject):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="reader_knowledge"
    )
    work = models.ForeignKey("stories.Work", null=True, blank=True, on_delete=models.PROTECT)
    subject_type = models.CharField(max_length=40)
    title = models.CharField(max_length=240)
    knowledge_statement = models.TextField()
    certainty = models.CharField(max_length=24, default="ambiguous")
    status = models.CharField(max_length=32, default="current")
    learned_story_time = models.CharField(max_length=160, blank=True)
    chapter = models.ForeignKey("stories.Chapter", null=True, blank=True, on_delete=models.PROTECT)
    scene = models.ForeignKey("scenes.Scene", null=True, blank=True, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class CharacterKnowledgeRecord(KnowledgeSubject):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="character_knowledge"
    )
    character = models.ForeignKey(
        "characters.Character", on_delete=models.PROTECT, related_name="knowledge_records"
    )
    work = models.ForeignKey("stories.Work", null=True, blank=True, on_delete=models.PROTECT)
    knowledge_statement = models.TextField()
    knowledge_state = models.CharField(max_length=24, default="knows")
    certainty = models.CharField(max_length=24, default="uncertain")
    source = models.TextField(blank=True)
    learned_story_time = models.CharField(max_length=160, blank=True)
    chapter = models.ForeignKey("stories.Chapter", null=True, blank=True, on_delete=models.PROTECT)
    scene = models.ForeignKey("scenes.Scene", null=True, blank=True, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("character", "secret", "thread", "learned_story_time"),
                name="character_subject_time_uniq",
            )
        ]

    def __str__(self):
        return f"{self.character}: {self.knowledge_state}"
