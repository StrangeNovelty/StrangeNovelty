import re
from typing import cast

from django import forms

from ai_assistance.services import MAX_INSTRUCTION_CHARACTERS
from scenes.content import MAX_CONTENT_CHARACTERS

KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")


class AIRequestForm(forms.Form):
    instruction = forms.CharField(
        max_length=MAX_INSTRUCTION_CHARACTERS,
        strip=True,
        widget=forms.Textarea(attrs={"rows": 5}),
        label="Review instruction",
    )
    idempotency_key = forms.CharField(max_length=128, widget=forms.HiddenInput())

    def clean_idempotency_key(self) -> str:
        key = cast(str, self.cleaned_data["idempotency_key"])
        if not KEY_PATTERN.fullmatch(key):
            raise forms.ValidationError("The request identifier is invalid.")
        return key


class AISuggestionApplyForm(forms.Form):
    review_text = forms.CharField(
        required=False,
        max_length=MAX_CONTENT_CHARACTERS,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 24}),
        label="Complete reviewed proposal",
    )
    idempotency_key = forms.CharField(max_length=128, widget=forms.HiddenInput())

    def clean_idempotency_key(self) -> str:
        key = cast(str, self.cleaned_data["idempotency_key"])
        if not KEY_PATTERN.fullmatch(key):
            raise forms.ValidationError("The save request identifier is invalid.")
        return key
