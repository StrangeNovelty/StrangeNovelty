import uuid

from django.core.exceptions import ValidationError
from django.db import models

from workspaces.models import Workspace


class Confidence(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"
    UNKNOWN = "unknown", "Unknown"


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    NEEDS_CORRECTION = "needs_correction", "Needs correction"
    NEEDS_SYMBOL_REVIEW = "needs_symbol_review", "Needs symbol review"
    APPROVED = "approved", "Approved"
    REJECTED_DUPLICATE = "rejected_duplicate", "Rejected as duplicate"
    INTENTIONALLY_EXCLUDED = "intentionally_excluded", "Intentionally excluded"


class Deck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="decks")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    edition = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=32, default="active")
    source_identity = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "source_identity"), name="deck_workspace_source_uniq"
            )
        ]

    def __str__(self) -> str:
        return self.name


class DeckExpansion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="expansions")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    source_identity = models.CharField(max_length=240)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("deck", "source_identity"), name="expansion_deck_source_uniq"
            )
        ]

    def __str__(self) -> str:
        return self.name


class DeckCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="categories")
    expansion = models.ForeignKey(
        DeckExpansion, on_delete=models.PROTECT, null=True, blank=True, related_name="categories"
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    source_identity = models.CharField(max_length=240)

    class Meta:
        ordering = ("order", "name", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("deck", "source_identity"), name="category_deck_source_uniq"
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.expansion_id and self.expansion.deck_id != self.deck_id:
            raise ValidationError({"expansion": "Expansion must belong to this Deck."})


class DeckCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="cards")
    expansion = models.ForeignKey(
        DeckExpansion, on_delete=models.PROTECT, null=True, blank=True, related_name="cards"
    )
    category = models.ForeignKey(
        DeckCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="cards"
    )
    stable_source_identity = models.CharField(max_length=240)
    card_number = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=500, blank=True)
    prompt = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    examples = models.TextField(blank=True)
    back_content = models.TextField(blank=True)
    suit = models.CharField(max_length=160, blank=True)
    mechanical_color = models.CharField(max_length=160, blank=True)
    role = models.CharField(max_length=300, blank=True)
    modifiers = models.JSONField(default=list, blank=True)
    symbols = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    source_file_label = models.CharField(max_length=500, blank=True)
    source_archive_label = models.CharField(max_length=500, blank=True)
    source_page = models.PositiveIntegerField(null=True, blank=True)
    source_position = models.CharField(max_length=160, blank=True)
    source_checksum = models.CharField(max_length=64, blank=True)
    import_checksum = models.CharField(max_length=64)
    extraction_confidence = models.CharField(
        max_length=16, choices=Confidence.choices, default=Confidence.UNKNOWN
    )
    review_status = models.CharField(
        max_length=32, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    review_notes = models.TextField(blank=True)
    author_notes = models.TextField(blank=True)
    original_extracted_snapshot = models.JSONField(default=dict)
    has_missing_text = models.BooleanField(default=False)
    has_ambiguous_wording = models.BooleanField(default=False)
    requires_symbol_review = models.BooleanField(default=False)
    is_custom = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("deck__name", "expansion__order", "card_number", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("deck", "stable_source_identity"), name="card_deck_source_uniq"
            )
        ]
        indexes = [
            models.Index(fields=("deck", "review_status"), name="deck_card_review_idx"),
            models.Index(fields=("deck", "extraction_confidence"), name="deck_card_conf_idx"),
        ]

    def __str__(self) -> str:
        return self.title or f"Card {self.card_number}"

    def clean(self) -> None:
        if self.expansion_id and self.expansion.deck_id != self.deck_id:
            raise ValidationError({"expansion": "Expansion must belong to this Deck."})
        if self.category_id and self.category.deck_id != self.deck_id:
            raise ValidationError({"category": "Category must belong to this Deck."})
        if (
            self.category_id
            and self.category.expansion_id
            and self.category.expansion_id != self.expansion_id
        ):
            raise ValidationError({"category": "Category Expansion must match the Card Expansion."})


class DeckCardCue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card = models.ForeignKey(DeckCard, on_delete=models.CASCADE, related_name="cues")
    cue_type = models.CharField(max_length=80, blank=True)
    cue_label = models.CharField(max_length=200, blank=True)
    cue_text = models.TextField(blank=True)
    order = models.PositiveIntegerField()
    symbol = models.CharField(max_length=160, blank=True)
    semantic_label = models.CharField(max_length=200, blank=True)
    meaning = models.TextField(blank=True)
    orientation = models.CharField(max_length=80, blank=True)
    source_provenance = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("card", "order"), name="cue_card_order_uniq")
        ]

    def __str__(self) -> str:
        return self.cue_label or self.cue_type or f"Cue {self.order}"


class ReviewableSourceRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    order = models.PositiveIntegerField(default=0)
    source_provenance = models.JSONField(default=dict)
    extraction_confidence = models.CharField(
        max_length=16, choices=Confidence.choices, default=Confidence.UNKNOWN
    )
    review_status = models.CharField(
        max_length=32, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DeckRule(ReviewableSourceRecord):
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="rules")
    expansion = models.ForeignKey(
        DeckExpansion, on_delete=models.PROTECT, null=True, blank=True, related_name="rules"
    )
    stable_source_identity = models.CharField(max_length=240)
    rule_type = models.CharField(max_length=120, blank=True)
    rule_text = models.TextField()

    class Meta:
        ordering = ("deck__name", "expansion__order", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("deck", "stable_source_identity"), name="rule_deck_source_uniq"
            )
        ]

    def __str__(self) -> str:
        return self.title


class SpreadTemplate(ReviewableSourceRecord):
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="spreads")
    expansion = models.ForeignKey(
        DeckExpansion, on_delete=models.PROTECT, null=True, blank=True, related_name="spreads"
    )
    stable_source_identity = models.CharField(max_length=240)
    purpose = models.TextField(blank=True)
    instructions = models.TextField()
    minimum_cards = models.PositiveIntegerField(default=0)
    maximum_cards = models.PositiveIntegerField(default=0)
    allows_redraw = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("deck__name", "expansion__order", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("deck", "stable_source_identity"), name="spread_deck_source_uniq"
            )
        ]

    def __str__(self) -> str:
        return self.title


class SpreadPosition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spread = models.ForeignKey(SpreadTemplate, on_delete=models.CASCADE, related_name="positions")
    order = models.PositiveIntegerField()
    name = models.CharField(max_length=300)
    meaning = models.TextField(blank=True)
    required_category = models.ForeignKey(
        DeckCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="spread_positions",
    )
    required_category_label = models.CharField(max_length=160, blank=True)
    is_optional = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("spread", "order"), name="spread_position_order_uniq")
        ]

    def __str__(self) -> str:
        return self.name


class JournalTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="journal_templates"
    )
    deck = models.ForeignKey(
        Deck, on_delete=models.PROTECT, null=True, blank=True, related_name="journals"
    )
    name = models.CharField(max_length=500)
    purpose = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    source_identity = models.CharField(max_length=240)
    source_provenance = models.JSONField(default=dict)
    review_status = models.CharField(
        max_length=32, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "source_identity"), name="journal_workspace_source_uniq"
            )
        ]

    def __str__(self) -> str:
        return self.name


class JournalSection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal = models.ForeignKey(JournalTemplate, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=500)
    guidance = models.TextField(blank=True)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("journal", "order"), name="journal_section_order_uniq")
        ]

    def __str__(self) -> str:
        return self.title


class JournalPrompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    section = models.ForeignKey(JournalSection, on_delete=models.CASCADE, related_name="prompts")
    label = models.CharField(max_length=500)
    prompt = models.TextField()
    response_type = models.CharField(max_length=80, blank=True)
    order = models.PositiveIntegerField()
    is_required = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("section", "order"), name="journal_prompt_order_uniq")
        ]

    def __str__(self) -> str:
        return self.label


class ImportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="deck_import_batches"
    )
    schema_version = models.PositiveIntegerField()
    source_package_checksum = models.CharField(max_length=64)
    source_collection_label = models.CharField(max_length=500)
    validation_status = models.CharField(max_length=16)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    unchanged_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    conflicted_count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    report = models.JSONField(default=dict)
    provenance = models.JSONField(default=dict)

    def __str__(self) -> str:
        return f"Deck import {self.id}"


class ImportSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="sources")
    stable_source_identity = models.CharField(max_length=500)
    path_label = models.CharField(max_length=500)
    checksum = models.CharField(max_length=64, blank=True)
    source_type = models.CharField(max_length=80)
    processing_status = models.CharField(max_length=80)
    report = models.JSONField(default=dict)

    def __str__(self) -> str:
        return self.path_label


class FavoriteCard(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="favorite_cards"
    )
    card = models.ForeignKey(DeckCard, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "card"), name="favorite_workspace_card_uniq"
            )
        ]

    def __str__(self) -> str:
        return f"Favorite: {self.card}"

    def clean(self) -> None:
        if self.card_id and self.card.deck.workspace_id != self.workspace_id:
            raise ValidationError({"card": "Card must belong to this Workspace."})


class SavedDraw(models.Model):
    class Mode(models.TextChoices):
        OFFICIAL = "official_spread", "Official spread"
        FREE = "free_draw", "Free draw"
        MANUAL = "manual_selection", "Manual selection"
        RANDOM = "random_draw", "Random draw"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INTERPRETED = "interpreted", "Interpreted"
        CONVERTED = "converted", "Converted"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT, related_name="saved_draws")
    title = models.CharField(max_length=240)
    primary_deck = models.ForeignKey(
        Deck, on_delete=models.PROTECT, null=True, blank=True, related_name="primary_draws"
    )
    spread = models.ForeignKey(
        SpreadTemplate, on_delete=models.PROTECT, null=True, blank=True, related_name="draws"
    )
    decks = models.ManyToManyField(Deck, through="DrawDeckSelection", related_name="draws")
    selected_expansions = models.ManyToManyField(
        DeckExpansion, blank=True, related_name="filtered_draws"
    )
    selected_categories = models.ManyToManyField(
        DeckCategory, blank=True, related_name="filtered_draws"
    )
    draw_mode = models.CharField(max_length=24, choices=Mode.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    random_seed = models.CharField(max_length=120, blank=True)
    work = models.ForeignKey(
        "stories.Work", on_delete=models.PROTECT, null=True, blank=True, related_name="deck_draws"
    )
    chapter = models.ForeignKey(
        "stories.Chapter",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deck_draws",
    )
    tone_guidance = models.TextField(blank=True)
    genre_guidance = models.TextField(blank=True)
    adult_audience_guidance = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    author_brief = models.TextField(blank=True)
    context_snapshot = models.JSONField(default=dict, blank=True)
    context_snapshot_at = models.DateTimeField(null=True, blank=True)
    allow_duplicates = models.BooleanField(default=False)
    include_pending = models.BooleanField(default=False)
    include_inactive = models.BooleanField(default=False)
    favorite_mode = models.CharField(
        max_length=16,
        choices=(
            ("all", "All cards"),
            ("only", "Favorites only"),
            ("exclude", "Exclude favorites"),
        ),
        default="all",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at", "id")
        indexes = [
            models.Index(fields=("workspace", "status", "-updated_at"), name="draw_ws_status_idx")
        ]

    def __str__(self):
        return self.title

    def clean(self) -> None:
        errors = {}
        for field in ("primary_deck", "spread", "work", "chapter"):
            value = getattr(self, field, None)
            if field != "spread" and value and value.workspace_id != self.workspace_id:
                errors[field] = "Selection must belong to this Workspace."
        if self.spread_id and self.spread.deck.workspace_id != self.workspace_id:
            errors["spread"] = "Spread must belong to this Workspace."
        if self.chapter_id and (not self.work_id or self.chapter.work_id != self.work_id):
            errors["chapter"] = "Chapter must belong to the selected Work."
        if errors:
            raise ValidationError(errors)


class DrawDeckSelection(models.Model):  # noqa: DJ008
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draw = models.ForeignKey(SavedDraw, on_delete=models.CASCADE, related_name="deck_selections")
    deck = models.ForeignKey(Deck, on_delete=models.PROTECT, related_name="draw_selections")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        constraints = [models.UniqueConstraint(fields=("draw", "deck"), name="draw_deck_uniq")]

    def clean(self):
        if self.deck_id and self.deck.workspace_id != self.draw.workspace_id:
            raise ValidationError({"deck": "Deck must belong to this Workspace."})


class DrawCard(models.Model):  # noqa: DJ008
    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        LOCKED = "locked", "Locked"
        REDRAWN = "redrawn", "Redrawn"
        REPLACED = "replaced", "Replaced"
        DISCARDED = "discarded", "Discarded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draw = models.ForeignKey(SavedDraw, on_delete=models.CASCADE, related_name="draw_cards")
    card = models.ForeignKey(DeckCard, on_delete=models.PROTECT, related_name="draw_occurrences")
    spread_position = models.ForeignKey(
        SpreadPosition, on_delete=models.PROTECT, null=True, blank=True, related_name="draw_cards"
    )
    position_order = models.PositiveIntegerField()
    custom_position_label = models.CharField(max_length=240, blank=True)
    orientation = models.CharField(
        max_length=16,
        choices=(("upright", "Upright"), ("reversed", "Reversed"), ("rotated", "Rotated")),
        default="upright",
    )
    state = models.CharField(max_length=16, choices=State.choices, default=State.ACTIVE)
    draw_sequence = models.PositiveIntegerField(default=1)
    author_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position_order", "draw_sequence", "id")
        constraints = [
            models.UniqueConstraint(fields=("draw", "position_order"), name="draw_position_uniq")
        ]

    def clean(self):
        errors = {}
        if self.card_id and self.card.deck.workspace_id != self.draw.workspace_id:
            errors["card"] = "Card must belong to this Workspace."
        if self.spread_position_id:
            if self.draw.spread_id != self.spread_position.spread_id:
                errors["spread_position"] = "Position must belong to this Draw's Spread."
            required = self.spread_position.required_category_id
            if required and self.card.category_id != required:
                errors["card"] = "Card does not satisfy the position's required Category."
        if errors:
            raise ValidationError(errors)


class DrawCardHistory(models.Model):  # noqa: DJ008
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draw = models.ForeignKey(SavedDraw, on_delete=models.CASCADE, related_name="card_history")
    draw_card = models.ForeignKey(
        DrawCard, on_delete=models.CASCADE, null=True, blank=True, related_name="history"
    )
    previous_card = models.ForeignKey(
        DeckCard, on_delete=models.PROTECT, null=True, blank=True, related_name="draw_history_from"
    )
    replacement_card = models.ForeignKey(
        DeckCard, on_delete=models.PROTECT, null=True, blank=True, related_name="draw_history_to"
    )
    action = models.CharField(max_length=40)
    sequence = models.PositiveIntegerField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sequence", "created_at", "id")


class DrawInterpretation(models.Model):  # noqa: DJ008
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draw = models.ForeignKey(SavedDraw, on_delete=models.CASCADE, related_name="interpretations")
    title = models.CharField(max_length=240)
    interpretation_text = models.TextField(blank=True)
    unresolved_questions = models.TextField(blank=True)
    opportunities = models.TextField(blank=True)
    risks_complications = models.TextField(blank=True)
    author_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=(
            ("draft", "Draft"),
            ("accepted", "Accepted"),
            ("revised", "Revised"),
            ("rejected", "Rejected"),
            ("unresolved", "Unresolved"),
            ("converted", "Converted"),
        ),
        default="draft",
    )
    provenance = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DrawContextBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draw = models.ForeignKey(SavedDraw, on_delete=models.CASCADE)
    role = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ("order", "id")

    def clean(self):
        for field in self._meta.fields:
            if isinstance(field, models.ForeignKey) and field.name != "draw":
                value = getattr(self, field.name, None)
                if value and value.workspace_id != self.draw.workspace_id:
                    raise ValidationError({field.name: "Context must belong to this Workspace."})


class DrawCharacterContext(DrawContextBase):  # noqa: DJ008
    character = models.ForeignKey("characters.Character", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [
            models.UniqueConstraint(fields=("draw", "character"), name="draw_character_uniq")
        ]


class DrawGroupContext(DrawContextBase):  # noqa: DJ008
    group = models.ForeignKey("characters.CharacterGroup", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [models.UniqueConstraint(fields=("draw", "group"), name="draw_group_uniq")]


class DrawLocationContext(DrawContextBase):  # noqa: DJ008
    location = models.ForeignKey("worldbuilding.Location", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [
            models.UniqueConstraint(fields=("draw", "location"), name="draw_location_uniq")
        ]


class DrawRegionContext(DrawContextBase):  # noqa: DJ008
    region = models.ForeignKey("worldbuilding.Region", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [models.UniqueConstraint(fields=("draw", "region"), name="draw_region_uniq")]


class DrawCodexContext(DrawContextBase):  # noqa: DJ008
    codex = models.ForeignKey("worldbuilding.CodexEntry", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [models.UniqueConstraint(fields=("draw", "codex"), name="draw_codex_uniq")]


class DrawItemContext(DrawContextBase):  # noqa: DJ008
    item = models.ForeignKey("worldbuilding.WorldItem", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [models.UniqueConstraint(fields=("draw", "item"), name="draw_item_uniq")]


class DrawCreatureContext(DrawContextBase):  # noqa: DJ008
    creature = models.ForeignKey("worldbuilding.Creature", on_delete=models.PROTECT)

    class Meta(DrawContextBase.Meta):
        constraints = [
            models.UniqueConstraint(fields=("draw", "creature"), name="draw_creature_uniq")
        ]


class DrawConversion(models.Model):  # noqa: DJ008
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interpretation = models.ForeignKey(
        DrawInterpretation, on_delete=models.PROTECT, related_name="conversions"
    )
    target_type = models.CharField(max_length=40)
    action = models.CharField(max_length=20, default="create")
    character = models.ForeignKey(
        "characters.Character", null=True, blank=True, on_delete=models.PROTECT
    )
    group = models.ForeignKey(
        "characters.CharacterGroup", null=True, blank=True, on_delete=models.PROTECT
    )
    location = models.ForeignKey(
        "worldbuilding.Location", null=True, blank=True, on_delete=models.PROTECT
    )
    region = models.ForeignKey(
        "worldbuilding.Region", null=True, blank=True, on_delete=models.PROTECT
    )
    codex = models.ForeignKey(
        "worldbuilding.CodexEntry", null=True, blank=True, on_delete=models.PROTECT
    )
    item = models.ForeignKey(
        "worldbuilding.WorldItem", null=True, blank=True, on_delete=models.PROTECT
    )
    creature = models.ForeignKey(
        "worldbuilding.Creature", null=True, blank=True, on_delete=models.PROTECT
    )
    chapter = models.ForeignKey("stories.Chapter", null=True, blank=True, on_delete=models.PROTECT)
    work = models.ForeignKey("stories.Work", null=True, blank=True, on_delete=models.PROTECT)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
