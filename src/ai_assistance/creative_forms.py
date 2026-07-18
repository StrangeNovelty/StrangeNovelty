from django import forms

from ai_assistance.models import AIChatSession, AIContextPack, BrainstormSession, VoiceProfile
from ai_assistance.tasks import TASKS
from characters.models import Character
from stories.models import Chapter
from timeline.models import Timeline
from worldbuilding.models import Location


class ContextPackForm(forms.ModelForm):
    class Meta:
        model = AIContextPack
        fields = (
            "name",
            "description",
            "work",
            "chapter",
            "voice_profile",
            "status",
            "author_instructions",
            "tone_guidance",
            "genre_guidance",
            "adult_audience_guidance",
            "exclusions",
            "prioritization_notes",
            "detail_level",
        )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work"].queryset = workspace.works.all()
        self.fields["chapter"].queryset = workspace.chapters.all()
        self.fields["voice_profile"].queryset = workspace.voice_profiles.all()


class VoiceProfileForm(forms.ModelForm):
    class Meta:
        model = VoiceProfile
        fields = (
            "work",
            "name",
            "description",
            "status",
            "source_notes",
            "prose_guidance",
            "dialogue_guidance",
            "sentence_rhythm",
            "paragraph_rhythm",
            "diction",
            "imagery",
            "humor",
            "emotional_distance",
            "exposition_approach",
            "prohibited_tendencies",
            "intentional_quirks",
        )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work"].queryset = workspace.works.all()


class CreativeRequestForm(forms.Form):
    task_key = forms.ChoiceField(choices=tuple((key, task.title) for key, task in TASKS.items()))
    context_pack = forms.ModelChoiceField(queryset=AIContextPack.objects.none(), required=False)
    instruction = forms.CharField(widget=forms.Textarea(attrs={"rows": 7}), max_length=8000)
    model_override = forms.CharField(
        required=False, max_length=160, help_text="Optional custom provider model identifier."
    )

    def __init__(self, *args, workspace, initial_task=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["context_pack"].queryset = workspace.ai_context_packs.exclude(status="archived")
        if initial_task:
            self.fields["task_key"].initial = initial_task


class ChatSessionForm(forms.ModelForm):
    class Meta:
        model = AIChatSession
        fields = ("title", "context_pack", "work", "chapter", "pinned_instructions")

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["context_pack"].queryset = workspace.ai_context_packs.exclude(status="archived")
        self.fields["work"].queryset = workspace.works.all()
        self.fields["chapter"].queryset = workspace.chapters.all()


class ChatMessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5}), max_length=8000, label="Message"
    )


class BrainstormSessionForm(forms.ModelForm):
    characters = forms.ModelMultipleChoiceField(
        queryset=Character.objects.none(),
        required=False,
        help_text="The Plot Seeds and NPC modes use only the cast you deliberately select.",
    )
    locations = forms.ModelMultipleChoiceField(
        queryset=Location.objects.none(),
        required=False,
        help_text="Places that define the immediate world context.",
    )
    threat_level = forms.ChoiceField(
        required=False,
        choices=(
            ("", "Let the session decide"),
            ("predator", "Predator"),
            ("exploiter", "Exploiter"),
            ("ideologue", "Ideologue"),
            ("gatekeeper", "Gatekeeper"),
            ("wild_card", "Wild Card"),
            ("reluctant_asset", "Reluctant Asset"),
        ),
    )
    discipline = forms.ChoiceField(
        required=False,
        choices=(
            ("", "Open discipline"),
            ("arcane", "Arcane"),
            ("organic", "Organic"),
            ("alchemical", "Alchemical"),
            ("mechanical", "Mechanical"),
            ("hybrid", "Hybrid"),
        ),
    )

    class Meta:
        model = BrainstormSession
        fields = ("title", "mode", "work", "chapter", "draw", "focus", "exclusions", "author_notes")
        widgets = {
            "focus": forms.Textarea(attrs={"rows": 4}),
            "exclusions": forms.Textarea(attrs={"rows": 3}),
            "author_notes": forms.Textarea(attrs={"rows": 7}),
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["work"].queryset = workspace.works.all()
        self.fields["chapter"].queryset = workspace.chapters.all()
        self.fields["draw"].queryset = workspace.saved_draws.all()
        self.fields["characters"].queryset = workspace.characters.exclude(status="archived")
        self.fields["locations"].queryset = workspace.locations.exclude(status="archived")
        if self.instance and self.instance.pk:
            pack = self.instance.context_pack
            self.fields["characters"].initial = [
                link.character_id for link in pack.aicontextcharacterlink_set.all()
            ]
            self.fields["locations"].initial = [
                link.location_id for link in pack.aicontextlocationlink_set.all()
            ]
            self.fields["threat_level"].initial = self.instance.mode_settings.get(
                "threat_level", ""
            )
            self.fields["discipline"].initial = self.instance.mode_settings.get("discipline", "")

    def clean(self):
        cleaned = super().clean()
        work = cleaned.get("work")
        chapter = cleaned.get("chapter")
        if chapter and work and chapter.work_id != work.id:
            self.add_error("chapter", "Chapter must belong to the selected Work.")
        return cleaned


class CreativeReviewForm(forms.Form):
    reviewed_output = forms.CharField(widget=forms.Textarea(attrs={"rows": 28}), max_length=200_000)
    review_notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)


class ConversionForm(forms.Form):
    target_type = forms.ChoiceField(
        choices=(
            ("character", "Character"),
            ("location", "Location"),
            ("region", "Region"),
            ("creature", "Creature"),
            ("item", "World Item"),
            ("plot_thread", "Plot Thread"),
            ("timeline_event", "Planned Timeline Event"),
            ("voice_profile", "Voice Profile"),
            ("chapter_concept", "Chapter concept"),
            ("chapter_outline", "Chapter outline"),
            ("chapter_notes", "Chapter notes"),
        )
    )
    action = forms.ChoiceField(
        choices=(
            ("create", "Create a new record"),
            ("append", "Append to selected field"),
            ("replace", "Replace selected field"),
        ),
        initial="create",
        required=False,
    )
    title = forms.CharField(max_length=240)
    content = forms.CharField(widget=forms.Textarea(attrs={"rows": 16}), max_length=200_000)
    timeline = forms.ModelChoiceField(queryset=Timeline.objects.none(), required=False)
    chapter = forms.ModelChoiceField(queryset=Chapter.objects.none(), required=False)

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timeline"].queryset = workspace.timelines.all()
        self.fields["chapter"].queryset = workspace.chapters.all()

    def clean(self):
        cleaned = super().clean()
        target_type = cleaned.get("target_type", "")
        action = cleaned.get("action") or "create"
        cleaned["action"] = action
        if target_type.startswith("chapter_"):
            if not cleaned.get("chapter"):
                self.add_error("chapter", "Select the Chapter to update.")
            if action == "create":
                self.add_error("action", "Chapter fields use append or replace.")
        elif action != "create":
            self.add_error("action", "New native records use Create.")
        if target_type == "timeline_event" and not cleaned.get("timeline"):
            self.add_error("timeline", "Select a Timeline for the planned Event.")
        return cleaned
