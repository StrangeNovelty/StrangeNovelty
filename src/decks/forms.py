import json

from django import forms

from decks.models import DeckCard, DeckCardCue, ReviewStatus
from workspaces.models import Workspace


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
