import uuid

from django.core.exceptions import ValidationError
from django.db import models


class BrainstormCardSelection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        "ai_assistance.BrainstormSession", on_delete=models.CASCADE, related_name="card_selections"
    )
    card = models.ForeignKey(
        "decks.DeckCard",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="brainstorm_selections",
    )
    manual_text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("session", "order"), name="next_brainstorm_card_order_uniq"
            )
        ]

    def __str__(self):
        return self.manual_text or str(self.card)

    def clean(self):
        if bool(self.card_id) == bool(self.manual_text.strip()):
            raise ValidationError("Choose one imported Card or enter one manual Card.")
        if self.card_id and self.card.deck.workspace_id != self.session.workspace_id:
            raise ValidationError("Card must belong to this Workspace.")


class WorldBibleEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.PROTECT, related_name="world_bible_entries"
    )
    title = models.CharField(max_length=240)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("order", "title", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "title"), name="next_world_bible_title_uniq"
            )
        ]

    def __str__(self):
        return self.title
