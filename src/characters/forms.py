from typing import cast

from django import forms
from django.db.models import Q, QuerySet

from characters.models import Ability, AbilityEvent, AbilityPrediction, AbilityStage, Character
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


class AbilityForm(forms.ModelForm):
    class Meta:
        model = Ability
        fields = (
            "name",
            "category",
            "description",
            "limitations",
            "costs",
            "mastery",
            "status",
            "notes",
        )
        labels = {
            "category": "Category or type",
            "description": "Current description",
            "costs": "Costs or consequences",
            "mastery": "Current mastery",
            "notes": "Ability notes",
        }
        help_texts = {
            "category": "A broad creative label such as magic, craft, social, or physical.",
            "mastery": "How developed the ability is now.",
            "status": "Whether the ability is currently available to the Character.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "limitations": forms.Textarea(attrs={"rows": 4}),
            "costs": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_name(self) -> str:
        name = cast(str, self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Ability name is required.")
        return name


class AbilityStageForm(forms.ModelForm):
    class Meta:
        model = AbilityStage
        fields = ("name", "order", "state", "description", "requirements", "costs")
        labels = {
            "order": "Stage order",
            "requirements": "Requirements or catalyst",
            "costs": "Limitations or costs at this stage",
        }
        help_texts = {
            "order": "Lower numbers appear first.",
            "state": "Marking this stage current moves the previous current stage to past.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "costs": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_name(self) -> str:
        name = cast(str, self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Stage name is required.")
        return name


class AbilityEventForm(forms.ModelForm):
    class Meta:
        model = AbilityEvent
        fields = (
            "title",
            "event_type",
            "event_date",
            "story_time",
            "description",
            "scene",
        )
        labels = {
            "event_date": "Calendar date",
            "story_time": "Story-time label",
            "scene": "Linked Scene",
        }
        help_texts = {
            "event_date": "Optional; useful when the story uses calendar dates.",
            "story_time": "Optional freeform timing, such as “after the siege” or “Act II.”",
            "scene": "Only Scenes in this Workspace are available.",
        }
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        allowed = Q(lifecycle=Scene.Lifecycle.ACTIVE)
        if self.instance.pk and self.instance.scene_id:
            allowed |= Q(id=self.instance.scene_id)
        self.fields["scene"].queryset = (
            Scene.objects.filter(workspace=workspace)
            .filter(allowed)
            .exclude(lifecycle=Scene.Lifecycle.TRASHED)
            .order_by("ordering", "id")
        )

    def clean_title(self) -> str:
        title = cast(str, self.cleaned_data["title"]).strip()
        if not title:
            raise forms.ValidationError("Event title is required.")
        return title


class AbilityPredictionForm(forms.ModelForm):
    class Meta:
        model = AbilityPrediction
        fields = ("title", "prediction", "rationale", "status", "notes")
        help_texts = {
            "prediction": "A private possibility, not established story canon.",
            "rationale": "Why this development seems plausible.",
            "status": "Track whether the possibility remains active or how it resolved.",
        }
        widgets = {
            "prediction": forms.Textarea(attrs={"rows": 5}),
            "rationale": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_title(self) -> str:
        title = cast(str, self.cleaned_data["title"]).strip()
        if not title:
            raise forms.ValidationError("Prediction title is required.")
        return title

    def clean_prediction(self) -> str:
        prediction = cast(str, self.cleaned_data["prediction"]).strip()
        if not prediction:
            raise forms.ValidationError("Prediction is required.")
        return prediction
