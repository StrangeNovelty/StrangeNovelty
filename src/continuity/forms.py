from django import forms

from continuity.models import (
    CharacterKnowledgeRecord,
    PlotThread,
    ReaderKnowledgeRecord,
    Secret,
    ThreadClue,
    ThreadProgressEvent,
    ThreadReveal,
)


class ThreadOverviewForm(forms.ModelForm):
    class Meta:
        model = PlotThread
        fields = (
            "work",
            "volume",
            "arc",
            "title",
            "thread_type",
            "status",
            "priority",
            "visibility",
            "health",
            "short_summary",
            "introduced_story_time",
            "target_resolution_story_time",
            "next_action",
            "next_review_label",
            "blocker_notes",
        )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("work", "volume", "arc"):
            self.fields[name].queryset = self.fields[name].queryset.filter(workspace=workspace)


class ThreadPurposeForm(forms.ModelForm):
    class Meta:
        model = PlotThread
        fields = ("description", "intended_payoff", "resolution_notes", "resolved_story_time")
        widgets = {name: forms.Textarea(attrs={"rows": 7}) for name in fields}


class EventForm(forms.ModelForm):
    class Meta:
        model = ThreadProgressEvent
        fields = (
            "event_type",
            "title",
            "story_time_label",
            "calendar_date",
            "description",
            "chapter",
            "scene",
            "status_impact",
        )


class ClueForm(forms.ModelForm):
    class Meta:
        model = ThreadClue
        fields = (
            "clue_type",
            "title",
            "description",
            "status",
            "subtlety",
            "chapter",
            "scene",
            "intended_interpretation",
            "reader_interpretation_notes",
        )


class RevealForm(forms.ModelForm):
    class Meta:
        model = ThreadReveal
        fields = (
            "title",
            "reveal_type",
            "description",
            "status",
            "chapter",
            "scene",
            "target_audience",
            "consequences",
        )


class SecretForm(forms.ModelForm):
    class Meta:
        model = Secret
        fields = (
            "work",
            "thread",
            "title",
            "secret_type",
            "status",
            "truth_statement",
            "public_belief",
            "why_it_matters",
            "consequences_if_revealed",
            "intended_reveal",
            "notes",
        )


class ReaderKnowledgeForm(forms.ModelForm):
    class Meta:
        model = ReaderKnowledgeRecord
        fields = (
            "work",
            "subject_type",
            "title",
            "knowledge_statement",
            "certainty",
            "status",
            "learned_story_time",
            "chapter",
            "scene",
            "notes",
            "secret",
            "thread",
            "character_subject",
            "group_subject",
            "location",
            "region",
            "codex",
            "item",
            "creature",
        )


class CharacterKnowledgeForm(forms.ModelForm):
    class Meta:
        model = CharacterKnowledgeRecord
        fields = (
            "character",
            "work",
            "secret",
            "thread",
            "character_subject",
            "group_subject",
            "location",
            "region",
            "codex",
            "item",
            "creature",
            "knowledge_statement",
            "knowledge_state",
            "certainty",
            "source",
            "learned_story_time",
            "chapter",
            "scene",
            "notes",
        )


def scope_form(form, workspace):
    for field in form.fields.values():
        queryset = getattr(field, "queryset", None)
        if queryset is None:
            continue
        model = queryset.model
        if any(item.name == "workspace" for item in model._meta.fields) or model.__name__ in (
            "PlotThread",
            "Secret",
        ):
            field.queryset = queryset.filter(workspace=workspace)
    return form
