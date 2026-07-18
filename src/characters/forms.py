from typing import cast

from django import forms
from django.db.models import Q, QuerySet

from characters.models import (
    Ability,
    AbilityEvent,
    AbilityPrediction,
    AbilityStage,
    BorrowedAbilityLog,
    Character,
    CharacterGroup,
    CharacterMechanicMembership,
    CharacterPersonalityTrait,
    CharacterRelationship,
    GroupMembership,
    GroupRelationship,
)
from scenes.models import Scene
from stories.models import Work
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
            "age",
            "tags",
            "appearance",
            "distinctive_features",
            "clothing",
            "mannerisms",
            "sensory_presence",
            "personality",
            "temperament",
            "values",
            "fears",
            "wants",
            "contradictions",
            "habits",
            "backstory",
            "origins",
            "formative_events",
            "goals",
            "internal_conflict",
            "external_conflict",
            "voice_notes",
            "current_story_function",
            "intended_arc",
            "current_arc_phase",
            "arc_turning_points",
            "arc_questions",
            "arc_predictions",
            "evaluation_notes",
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
            name: forms.Textarea(attrs={"rows": 5})
            for name in fields
            if name not in {"name", "role", "status", "age"}
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


class BorrowedAbilityLogForm(forms.ModelForm):
    class Meta:
        model = BorrowedAbilityLog
        fields = (
            "borrowed_from",
            "ability",
            "ability_name",
            "chapter",
            "scene",
            "story_time",
            "cost_or_damage",
            "duration",
            "reduced_effectiveness",
            "limitation_triggered",
            "recovery",
            "lasting_consequence",
            "continuity_implications",
            "notes",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 2})
            for name in (
                "cost_or_damage",
                "reduced_effectiveness",
                "limitation_triggered",
                "recovery",
                "lasting_consequence",
                "continuity_implications",
                "notes",
            )
        }

    def __init__(self, *args, workspace, membership: CharacterMechanicMembership, **kwargs):
        super().__init__(*args, **kwargs)
        self.membership = membership
        self.instance.workspace = workspace
        self.instance.membership = membership
        self.fields["borrowed_from"].queryset = Character.objects.filter(
            workspace=workspace
        ).exclude(id=membership.character_id)
        self.fields["ability"].queryset = Ability.objects.filter(workspace=workspace)
        self.fields["chapter"].queryset = workspace.chapters.select_related("work").order_by(
            "work__title", "order"
        )
        self.fields["scene"].queryset = workspace.scenes.exclude(
            lifecycle=Scene.Lifecycle.TRASHED
        ).order_by("ordering")

    def clean(self):
        cleaned = super().clean()
        ability = cleaned.get("ability")
        source = cleaned.get("borrowed_from")
        if ability and source and ability.character_id != source.id:
            self.add_error("ability", "Choose an Ability owned by the source Character.")
        return cleaned


class CharacterMechanicSetupForm(forms.Form):
    work = forms.ModelChoiceField(queryset=Work.objects.none())
    name = forms.CharField(max_length=200, label="Mechanic name")
    designation_label = forms.CharField(max_length=120, initial="Designation")
    designation = forms.CharField(max_length=120, required=False)
    family_group = forms.ModelChoiceField(
        queryset=CharacterGroup.objects.none(), required=False, label="Family"
    )
    shared_abilities = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="One shared ability per line. Details can be refined in the database later.",
    )
    borrowing_rules = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))
    default_cost = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    reduced_effectiveness_rule = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    repetition_rule = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    recovery_rule = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    own_ability_rule = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    consequence_rule = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work"].queryset = Work.objects.filter(workspace=workspace)
        self.fields["family_group"].queryset = CharacterGroup.objects.filter(
            workspace=workspace, group_type=CharacterGroup.GroupType.FAMILY
        )


class CharacterCreateForm(CharacterForm):
    class Meta(CharacterForm.Meta):
        fields = ("name", "aliases", "role", "status", "summary")


class CharacterPersonalityTraitForm(forms.ModelForm):
    class Meta:
        model = CharacterPersonalityTrait
        fields = ("name", "score", "low_label", "high_label", "notes", "order")
        labels = {
            "name": "Personality dimension",
            "score": "Position (-5 to 5)",
            "low_label": "Low-end meaning",
            "high_label": "High-end meaning",
        }
        widgets = {
            "score": forms.NumberInput(attrs={"type": "range", "min": -5, "max": 5}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


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


class CharacterRelationshipForm(forms.Form):
    other_character = forms.ModelChoiceField(
        queryset=Character.objects.none(),
        label="Other Character",
        empty_label="Choose a Character",
    )
    relationship_type = forms.ChoiceField(
        choices=CharacterRelationship.RelationshipType.choices,
        label="Relationship type",
    )
    short_label = forms.CharField(
        max_length=160,
        required=False,
        label="Short label",
        help_text="A compact description such as estranged sisters or reluctant allies.",
    )
    summary = forms.CharField(
        required=False,
        label="Summary or dynamic",
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    current_perspective = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    other_perspective = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    status = forms.ChoiceField(
        choices=CharacterRelationship.Status.choices,
        help_text="How this connection currently stands, separate from its type.",
    )
    knowledge_state = forms.ChoiceField(
        choices=CharacterRelationship.KnowledgeState.choices,
        label="Visibility or knowledge state",
        help_text="Who knows or recognizes that this relationship exists.",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        current_character: Character,
        relationship: CharacterRelationship | None = None,
        **kwargs: object,
    ) -> None:
        initial = dict(cast(dict[str, object], kwargs.pop("initial", {})))
        if relationship is not None:
            current_is_source = relationship.source_id == current_character.id
            initial.update(
                {
                    "other_character": (
                        relationship.target if current_is_source else relationship.source
                    ),
                    "relationship_type": relationship.relationship_type,
                    "short_label": relationship.short_label,
                    "summary": relationship.summary,
                    "current_perspective": (
                        relationship.source_perspective
                        if current_is_source
                        else relationship.target_perspective
                    ),
                    "other_perspective": (
                        relationship.target_perspective
                        if current_is_source
                        else relationship.source_perspective
                    ),
                    "status": relationship.status,
                    "knowledge_state": relationship.knowledge_state,
                    "notes": relationship.notes,
                }
            )
        else:
            initial.setdefault("status", CharacterRelationship.Status.ACTIVE)
            initial.setdefault("knowledge_state", CharacterRelationship.KnowledgeState.PRIVATE)
        super().__init__(*args, initial=initial, **kwargs)
        self.fields["other_character"].queryset = Character.objects.filter(
            workspace=workspace
        ).exclude(id=current_character.id)
        self.fields["current_perspective"].label = f"{current_character.name}’s perspective"
        self.fields["other_perspective"].label = "Other Character’s perspective"


class CharacterGroupForm(forms.ModelForm):
    class Meta:
        model = CharacterGroup
        fields = (
            "name",
            "group_type",
            "status",
            "tagline",
            "description",
            "purpose",
            "alignment",
            "public_goals",
            "hidden_goals",
            "resources",
            "territory",
            "leadership_notes",
            "methods",
            "reputation",
            "allies",
            "enemies",
            "current_conflicts",
            "history",
            "notes",
        )
        labels = {
            "group_type": "Group type",
            "tagline": "Tagline or short summary",
            "purpose": "Goals or purpose",
            "notes": "Group notes",
        }
        help_texts = {
            "group_type": "The broad shape of this connection in the cast.",
            "status": "Whether the Group currently operates in the story.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "purpose": forms.Textarea(attrs={"rows": 5}),
            "public_goals": forms.Textarea(attrs={"rows": 4}),
            "hidden_goals": forms.Textarea(attrs={"rows": 4}),
            "resources": forms.Textarea(attrs={"rows": 4}),
            "territory": forms.Textarea(attrs={"rows": 4}),
            "leadership_notes": forms.Textarea(attrs={"rows": 4}),
            "methods": forms.Textarea(attrs={"rows": 4}),
            "reputation": forms.Textarea(attrs={"rows": 4}),
            "allies": forms.Textarea(attrs={"rows": 4}),
            "enemies": forms.Textarea(attrs={"rows": 4}),
            "current_conflicts": forms.Textarea(attrs={"rows": 4}),
            "history": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_name(self) -> str:
        name = cast(str, self.cleaned_data["name"]).strip()
        if not name:
            raise forms.ValidationError("Group name is required.")
        return name

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["alignment"].required = False

    def clean_alignment(self) -> str:
        return cast(str, self.cleaned_data.get("alignment") or CharacterGroup.Alignment.UNKNOWN)


class CharacterGroupSearchForm(forms.Form):
    query = forms.CharField(max_length=200, strip=True, label="Search Groups")


class GroupMembershipForm(forms.ModelForm):
    class Meta:
        model = GroupMembership
        fields = (
            "character",
            "role",
            "status",
            "rank_label",
            "joined_story_time",
            "left_story_time",
            "notes",
        )
        labels = {
            "rank_label": "Rank or order label",
            "joined_story_time": "Joined story-time label",
            "left_story_time": "Left story-time label",
            "notes": "Membership notes",
        }
        help_texts = {
            "status": "The Character’s standing here, separate from the Group’s status.",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["character"].queryset = Character.objects.filter(workspace=workspace)


class GroupRelationshipForm(forms.Form):
    other_group = forms.ModelChoiceField(queryset=CharacterGroup.objects.none())
    relationship_type = forms.ChoiceField(choices=GroupRelationship.RelationshipType.choices)
    summary = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    current_perspective = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    other_perspective = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(
        self, *args: object, workspace: Workspace, group: CharacterGroup, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["other_group"].queryset = CharacterGroup.objects.filter(
            workspace=workspace
        ).exclude(id=group.id)


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
