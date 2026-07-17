from django import forms

from timeline.models import Timeline, TimelineEvent, TimelineEventRelation


class TimelineForm(forms.ModelForm):
    class Meta:
        model = Timeline
        fields = (
            "work",
            "name",
            "timeline_type",
            "status",
            "description",
            "calendar_system_label",
            "epoch_notes",
            "display_order",
        )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work"].queryset = workspace.works.all()


class EventOverviewForm(forms.ModelForm):
    class Meta:
        model = TimelineEvent
        fields = (
            "timeline",
            "work",
            "title",
            "event_type",
            "status",
            "significance",
            "visibility",
            "short_summary",
        )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timeline"].queryset = workspace.timelines.all()
        self.fields["work"].queryset = workspace.works.all()


class EventChronologyForm(forms.ModelForm):
    class Meta:
        model = TimelineEvent
        fields = (
            "chronology_precision",
            "start_sort_value",
            "end_sort_value",
            "display_date",
            "end_label",
            "era_label",
            "uncertainty_notes",
        )


class EventNarrativeForm(forms.ModelForm):
    class Meta:
        model = TimelineEvent
        fields = ("description", "consequences", "notes")


class RelationForm(forms.ModelForm):
    class Meta:
        model = TimelineEventRelation
        fields = ("target", "relation_type", "notes", "confidence")

    def __init__(self, *args, workspace, source=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = workspace.timeline_events.all()
        if source:
            queryset = queryset.exclude(id=source.id)
        self.fields["target"].queryset = queryset
