from typing import cast

from django import forms
from django.db.models import QuerySet

from characters.models import Character
from scenes.models import Scene
from workspaces.models import Workspace


class CharacterForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = (
            "name",
            "aliases",
            "role",
            "status",
            "summary",
            "appearance",
            "personality",
            "goals",
            "internal_conflict",
            "external_conflict",
            "voice_notes",
            "notes",
        )
        labels = {
            "aliases": "Aliases",
            "internal_conflict": "Internal conflict",
            "external_conflict": "External conflict",
            "voice_notes": "Voice notes",
            "notes": "General notes",
        }
        help_texts = {
            "aliases": "Enter one alias per line.",
            "role": "Their narrative function, such as protagonist, rival, or confidant.",
            "status": "Their current story condition, such as active, missing, or deceased.",
        }
        widgets = {
            "aliases": forms.Textarea(attrs={"rows": 3}),
            "summary": forms.Textarea(attrs={"rows": 4}),
            "appearance": forms.Textarea(attrs={"rows": 5}),
            "personality": forms.Textarea(attrs={"rows": 5}),
            "goals": forms.Textarea(attrs={"rows": 5}),
            "internal_conflict": forms.Textarea(attrs={"rows": 5}),
            "external_conflict": forms.Textarea(attrs={"rows": 5}),
            "voice_notes": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 6}),
        }

    def clean_name(self) -> str:
        name = cast(str, self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        return name

    def clean_aliases(self) -> str:
        aliases = cast(str, self.cleaned_data["aliases"])
        normalized: list[str] = []
        seen: set[str] = set()
        for line in aliases.splitlines():
            alias = line.strip()
            key = alias.casefold()
            if alias and key not in seen:
                normalized.append(alias)
                seen.add(key)
        return "\n".join(normalized)


class CharacterCreateForm(CharacterForm):
    class Meta(CharacterForm.Meta):
        fields = ("name", "aliases", "role", "status", "summary")


class CharacterListSearchForm(forms.Form):
    query = forms.CharField(max_length=200, strip=True, label="Search Characters")


class CharacterSceneLinkForm(forms.Form):
    scene = forms.ModelChoiceField(queryset=Scene.objects.none(), empty_label="Choose a Scene")

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        character: Character,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        linked_scene_ids = character.scene_links.values_list("scene_id", flat=True)
        queryset: QuerySet[Scene] = Scene.objects.filter(
            workspace=workspace, lifecycle=Scene.Lifecycle.ACTIVE
        ).exclude(id__in=linked_scene_ids)
        self.fields["scene"].queryset = queryset


class SceneCharacterSelectorForm(forms.Form):
    characters = forms.ModelMultipleChoiceField(
        queryset=Character.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 7}),
        label="Characters in this Scene",
    )

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["characters"].queryset = Character.objects.filter(workspace=workspace)
