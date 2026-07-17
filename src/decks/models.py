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
