import re
from typing import cast

from django import forms

from scenes.content import MAX_CONTENT_CHARACTERS
from scenes.services import MAX_TITLE_CHARACTERS

IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{16,128}$")


class SceneCreateForm(forms.Form):
    title = forms.CharField(max_length=MAX_TITLE_CHARACTERS, strip=True, label="Scene title")


class SceneSaveForm(forms.Form):
    content = forms.CharField(
        required=False,
        max_length=MAX_CONTENT_CHARACTERS,
        strip=False,
        widget=forms.Textarea(attrs={"rows": 28, "spellcheck": "true"}),
        label="Scene content",
    )
    expected_current_revision_id = forms.UUIDField(widget=forms.HiddenInput())
    expected_scene_version = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    idempotency_key = forms.CharField(max_length=128, widget=forms.HiddenInput())
    save_intent = forms.ChoiceField(
        choices=(("explicit_save", "Explicit save"),), widget=forms.HiddenInput()
    )

    def clean_idempotency_key(self) -> str:
        key = cast(str, self.cleaned_data["idempotency_key"])
        if not IDEMPOTENCY_KEY_PATTERN.fullmatch(key):
            raise forms.ValidationError("The save request identifier is invalid.")
        return key
