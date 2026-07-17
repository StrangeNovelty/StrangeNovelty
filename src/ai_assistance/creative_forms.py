from django import forms

from ai_assistance.models import AIChatSession, AIContextPack, VoiceProfile
from ai_assistance.tasks import TASKS
from timeline.models import Timeline


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


class CreativeReviewForm(forms.Form):
    reviewed_output = forms.CharField(widget=forms.Textarea(attrs={"rows": 28}), max_length=200_000)
    review_notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)


class ConversionForm(forms.Form):
    target_type = forms.ChoiceField(
        choices=(
            ("character", "Character"),
            ("creature", "Creature"),
            ("item", "World Item"),
            ("plot_thread", "Plot Thread"),
            ("timeline_event", "Planned Timeline Event"),
            ("voice_profile", "Voice Profile"),
        )
    )
    title = forms.CharField(max_length=240)
    content = forms.CharField(widget=forms.Textarea(attrs={"rows": 16}), max_length=200_000)
    timeline = forms.ModelChoiceField(queryset=Timeline.objects.none(), required=False)

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timeline"].queryset = workspace.timelines.all()
