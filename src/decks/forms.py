import json

from django import forms

from characters.models import Character, CharacterGroup
from decks.models import (
    Deck,
    DeckCard,
    DeckCardCue,
    DeckCategory,
    DeckExpansion,
    DrawInterpretation,
    ReviewStatus,
    SavedDraw,
    SpreadTemplate,
)
from stories.models import Chapter, Work
from workspaces.models import Workspace
from worldbuilding.models import CodexEntry, Creature, Location, Region, WorldItem


class JsonListField(forms.CharField):
    widget = forms.Textarea(attrs={"rows": 3})

    def prepare_value(self, value):
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False, indent=2)
        return value

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError("Enter a valid JSON list.") from exc
        if not isinstance(parsed, list):
            raise forms.ValidationError("Value must be a JSON list.")
        return parsed


class DeckCardReviewForm(forms.ModelForm):
    modifiers = JsonListField(required=False)
    symbols = JsonListField(required=False)
    tags = JsonListField(required=False)

    class Meta:
        model = DeckCard
        fields = (
            "title",
            "prompt",
            "instructions",
            "examples",
            "back_content",
            "role",
            "suit",
            "mechanical_color",
            "modifiers",
            "symbols",
            "tags",
            "review_notes",
            "author_notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 4})
            for name in (
                "prompt",
                "instructions",
                "examples",
                "back_content",
                "review_notes",
                "author_notes",
            )
        }


class CustomCardForm(DeckCardReviewForm):
    class Meta(DeckCardReviewForm.Meta):
        fields = (
            "deck",
            "expansion",
            "category",
            "title",
            "prompt",
            "instructions",
            "examples",
            "role",
            "suit",
            "mechanical_color",
            "modifiers",
            "symbols",
            "tags",
            "author_notes",
            "is_active",
        )

    def __init__(self, *args, workspace: Workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deck"].queryset = self.fields["deck"].queryset.filter(workspace=workspace)
        self.fields["expansion"].queryset = self.fields["expansion"].queryset.filter(
            deck__workspace=workspace
        )
        self.fields["category"].queryset = self.fields["category"].queryset.filter(
            deck__workspace=workspace
        )


class CueSymbolForm(forms.ModelForm):
    class Meta:
        model = DeckCardCue
        fields = ("semantic_label", "meaning")


REVIEW_ACTIONS = {status for status, _ in ReviewStatus.choices}


class DrawSetupForm(forms.ModelForm):
    decks = forms.ModelMultipleChoiceField(queryset=Deck.objects.none())
    expansions = forms.ModelMultipleChoiceField(
        queryset=DeckExpansion.objects.none(), required=False
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=DeckCategory.objects.none(), required=False
    )
    card_count = forms.IntegerField(min_value=1, max_value=100, initial=3)
    characters = forms.ModelMultipleChoiceField(queryset=Character.objects.none(), required=False)
    groups = forms.ModelMultipleChoiceField(queryset=CharacterGroup.objects.none(), required=False)
    locations = forms.ModelMultipleChoiceField(queryset=Location.objects.none(), required=False)
    regions = forms.ModelMultipleChoiceField(queryset=Region.objects.none(), required=False)
    codex_entries = forms.ModelMultipleChoiceField(
        queryset=CodexEntry.objects.none(), required=False
    )
    items = forms.ModelMultipleChoiceField(queryset=WorldItem.objects.none(), required=False)
    creatures = forms.ModelMultipleChoiceField(queryset=Creature.objects.none(), required=False)

    class Meta:
        model = SavedDraw
        fields = (
            "title",
            "draw_mode",
            "decks",
            "expansions",
            "categories",
            "spread",
            "work",
            "chapter",
            "card_count",
            "favorite_mode",
            "include_pending",
            "include_inactive",
            "allow_duplicates",
            "tone_guidance",
            "genre_guidance",
            "adult_audience_guidance",
            "exclusions",
            "author_brief",
            "characters",
            "groups",
            "locations",
            "regions",
            "codex_entries",
            "items",
            "creatures",
        )
        widgets = {
            "tone_guidance": forms.Textarea(attrs={"rows": 2}),
            "genre_guidance": forms.Textarea(attrs={"rows": 2}),
            "adult_audience_guidance": forms.Textarea(attrs={"rows": 2}),
            "exclusions": forms.Textarea(attrs={"rows": 2}),
            "author_brief": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.instance.workspace = workspace
        mappings = {
            "decks": Deck.objects.filter(workspace=workspace),
            "expansions": DeckExpansion.objects.filter(deck__workspace=workspace, is_active=True),
            "categories": DeckCategory.objects.filter(deck__workspace=workspace),
            "spread": SpreadTemplate.objects.filter(deck__workspace=workspace, is_active=True),
            "work": Work.objects.filter(workspace=workspace),
            "chapter": Chapter.objects.filter(workspace=workspace),
            "characters": Character.objects.filter(workspace=workspace),
            "groups": CharacterGroup.objects.filter(workspace=workspace),
            "locations": Location.objects.filter(workspace=workspace),
            "regions": Region.objects.filter(workspace=workspace),
            "codex_entries": CodexEntry.objects.filter(workspace=workspace),
            "items": WorldItem.objects.filter(workspace=workspace),
            "creatures": Creature.objects.filter(workspace=workspace),
        }
        for name, queryset in mappings.items():
            self.fields[name].queryset = queryset

    def clean(self):
        cleaned = super().clean()
        work, chapter, spread = cleaned.get("work"), cleaned.get("chapter"), cleaned.get("spread")
        decks = cleaned.get("decks")
        if chapter and (not work or chapter.work_id != work.id):
            self.add_error("chapter", "Chapter must belong to the selected Work.")
        if spread and decks and spread.deck not in decks:
            self.add_error("spread", "The Spread's Deck must be selected.")
        if spread and cleaned.get("draw_mode") != SavedDraw.Mode.OFFICIAL:
            self.add_error("spread", "A Spread requires official-spread mode.")
        if decks:
            deck_ids = set(decks.values_list("id", flat=True))
            expansions = cleaned.get("expansions")
            categories = cleaned.get("categories")
            if expansions and expansions.exclude(deck_id__in=deck_ids).exists():
                self.add_error("expansions", "Expansion must belong to a selected Deck.")
            if categories and categories.exclude(deck_id__in=deck_ids).exists():
                self.add_error("categories", "Category must belong to a selected Deck.")
        return cleaned


class DrawInterpretationForm(forms.ModelForm):
    class Meta:
        model = DrawInterpretation
        fields = (
            "title",
            "interpretation_text",
            "unresolved_questions",
            "opportunities",
            "risks_complications",
            "author_notes",
            "status",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 5})
            for name in (
                "interpretation_text",
                "unresolved_questions",
                "opportunities",
                "risks_complications",
                "author_notes",
            )
        }


class DrawConversionForm(forms.Form):
    TARGETS = (
        ("character", "Character"),
        ("group", "Character Group"),
        ("location", "Location"),
        ("region", "Region"),
        ("codex", "Codex entry"),
        ("item", "World Item"),
        ("creature", "Creature"),
        ("chapter", "Chapter planning update"),
        ("work", "Work description append"),
    )
    target_type = forms.ChoiceField(choices=TARGETS)
    title = forms.CharField(max_length=240)
    content = forms.CharField(widget=forms.Textarea(attrs={"rows": 10}))
    chapter = forms.ModelChoiceField(queryset=Chapter.objects.none(), required=False)
    chapter_field = forms.ChoiceField(
        choices=(
            (name, name.replace("_", " ").title())
            for name in (
                "concept",
                "goal",
                "key_beats",
                "emotional_arc",
                "character_focus",
                "brain_dump",
                "outline",
                "notes",
            )
        ),
        required=False,
    )
    update_mode = forms.ChoiceField(
        choices=(("append", "Append"), ("replace", "Replace")), initial="append"
    )
    work = forms.ModelChoiceField(queryset=Work.objects.none(), required=False)

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["chapter"].queryset = Chapter.objects.filter(workspace=workspace)
        self.fields["work"].queryset = Work.objects.filter(workspace=workspace)
