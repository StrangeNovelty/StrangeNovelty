from django import forms

from characters.models import Character, CharacterGroup
from scenes.models import Scene
from workspaces.models import Workspace
from worldbuilding.models import CodexEntry, Creature, Location, Region, WorldItem


class ScopedModelForm(forms.ModelForm):
    def __init__(self, *args: object, workspace: Workspace, **kwargs: object) -> None:
        self.workspace = workspace
        super().__init__(*args, **kwargs)
        self.instance.workspace = workspace
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.queryset = field.queryset.filter(workspace=workspace)


class RegionForm(ScopedModelForm):
    class Meta:
        model = Region
        fields = (
            "name",
            "region_type",
            "status",
            "parent",
            "summary",
            "description",
            "geography",
            "climate",
            "cultures",
            "government",
            "notable_features",
            "hazards",
            "notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 5})
            for name in (
                "summary",
                "description",
                "geography",
                "climate",
                "cultures",
                "government",
                "notable_features",
                "hazards",
                "notes",
            )
        }

    def clean_parent(self) -> Region | None:
        parent = self.cleaned_data.get("parent")
        if parent and self.instance.pk and parent.pk == self.instance.pk:
            raise forms.ValidationError("A Region cannot parent itself.")
        return parent


class LocationForm(ScopedModelForm):
    class Meta:
        model = Location
        fields = (
            "name",
            "aliases",
            "location_type",
            "status",
            "region",
            "summary",
            "description",
            "history",
            "current_state",
            "atmosphere",
            "notable_features",
            "sensory_notes",
            "hazards",
            "culture",
            "travel_notes",
            "notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 5})
            for name in (
                "aliases",
                "summary",
                "description",
                "history",
                "current_state",
                "atmosphere",
                "notable_features",
                "sensory_notes",
                "hazards",
                "culture",
                "travel_notes",
                "notes",
            )
        }


class CodexEntryForm(ScopedModelForm):
    class Meta:
        model = CodexEntry
        fields = (
            "term",
            "aliases",
            "category",
            "status",
            "definition",
            "description",
            "implications",
            "related_terms",
            "canon_state",
            "provenance_note",
            "notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 5})
            for name in (
                "aliases",
                "definition",
                "description",
                "implications",
                "related_terms",
                "provenance_note",
                "notes",
            )
        }


class WorldItemForm(ScopedModelForm):
    class Meta:
        model = WorldItem
        fields = (
            "name",
            "aliases",
            "item_type",
            "status",
            "significance",
            "summary",
            "description",
            "appearance",
            "origin",
            "function",
            "capabilities",
            "limitations",
            "costs_dangers",
            "current_condition",
            "current_location",
            "notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 5})
            for name in (
                "aliases",
                "summary",
                "description",
                "appearance",
                "origin",
                "function",
                "capabilities",
                "limitations",
                "costs_dangers",
                "current_condition",
                "notes",
            )
        }


class CreatureForm(ScopedModelForm):
    class Meta:
        model = Creature
        fields = (
            "name",
            "aliases",
            "creature_type",
            "classification",
            "status",
            "threat_level",
            "intelligence",
            "summary",
            "appearance",
            "biology",
            "habitat",
            "behavior",
            "diet",
            "abilities",
            "weaknesses",
            "signs",
            "ecology",
            "origin",
            "cultural_significance",
            "encounter_notes",
            "notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 5})
            for name in (
                "aliases",
                "summary",
                "appearance",
                "biology",
                "habitat",
                "behavior",
                "diet",
                "abilities",
                "weaknesses",
                "signs",
                "ecology",
                "origin",
                "cultural_significance",
                "encounter_notes",
                "notes",
            )
        }


class WorldFilterForm(forms.Form):
    query = forms.CharField(required=False, max_length=200, label="Search")
    type = forms.CharField(required=False, max_length=30)
    status = forms.CharField(required=False, max_length=30)


class SceneWorldContextForm(forms.Form):
    primary_location = forms.ModelChoiceField(
        queryset=Location.objects.none(), required=False, empty_label="No primary Location"
    )
    locations = forms.ModelMultipleChoiceField(
        queryset=Location.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )
    regions = forms.ModelMultipleChoiceField(
        queryset=Region.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=CharacterGroup.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
        label="Groups or factions",
    )
    codex_entries = forms.ModelMultipleChoiceField(
        queryset=CodexEntry.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )
    items = forms.ModelMultipleChoiceField(
        queryset=WorldItem.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )
    creatures = forms.ModelMultipleChoiceField(
        queryset=Creature.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 5}),
    )

    def __init__(self, *args: object, workspace: Workspace, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        mappings = {
            "primary_location": Location,
            "locations": Location,
            "regions": Region,
            "groups": CharacterGroup,
            "codex_entries": CodexEntry,
            "items": WorldItem,
            "creatures": Creature,
        }
        for name, model in mappings.items():
            self.fields[name].queryset = model.objects.filter(workspace=workspace)


class WorldConnectionForm(forms.Form):
    character = forms.ModelChoiceField(queryset=Character.objects.none(), required=False)
    group = forms.ModelChoiceField(queryset=CharacterGroup.objects.none(), required=False)
    scene = forms.ModelChoiceField(queryset=Scene.objects.none(), required=False)
    location = forms.ModelChoiceField(queryset=Location.objects.none(), required=False)
    region = forms.ModelChoiceField(queryset=Region.objects.none(), required=False)
    codex_entry = forms.ModelChoiceField(queryset=CodexEntry.objects.none(), required=False)
    role = forms.CharField(max_length=40, required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args: object, workspace: Workspace, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["character"].queryset = Character.objects.filter(workspace=workspace)
        self.fields["group"].queryset = CharacterGroup.objects.filter(workspace=workspace)
        self.fields["scene"].queryset = Scene.objects.filter(
            workspace=workspace, lifecycle=Scene.Lifecycle.ACTIVE
        )
        self.fields["location"].queryset = Location.objects.filter(workspace=workspace)
        self.fields["region"].queryset = Region.objects.filter(workspace=workspace)
        self.fields["codex_entry"].queryset = CodexEntry.objects.filter(workspace=workspace)

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        targets = ("character", "group", "scene", "location", "region", "codex_entry")
        if sum(bool(cleaned.get(name)) for name in targets) != 1:
            raise forms.ValidationError("Choose exactly one record to connect.")
        return cleaned
