from django import forms

from publishing.models import (
    ManuscriptArtworkPlacement,
    ManuscriptEntry,
    ManuscriptGlossaryEntry,
    ManuscriptProject,
    PublicationEntry,
)
from publishing.profiles import PROFILES


class ManuscriptProjectForm(forms.ModelForm):
    class Meta:
        model = ManuscriptProject
        fields = (
            "work",
            "name",
            "manuscript_type",
            "status",
            "title_override",
            "subtitle_override",
            "author_name_override",
            "edition_label",
            "description",
            "front_matter_notes",
            "back_matter_notes",
            "formatting_profile",
            "formatting_overrides",
            "include_chapter_labels",
            "include_scene_titles",
            "include_chapter_summaries",
            "include_scene_breaks",
            "include_artwork",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 4})
            for name in ("description", "front_matter_notes", "back_matter_notes")
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.workspace = workspace
        self.fields["work"].queryset = workspace.works.all()
        self.fields["formatting_profile"].widget = forms.Select(
            choices=[(key, value.name) for key, value in PROFILES.items()]
        )


class ManuscriptEntryForm(forms.ModelForm):
    class Meta:
        model = ManuscriptEntry
        fields = (
            "order",
            "entry_type",
            "volume",
            "arc",
            "chapter",
            "scene",
            "custom_heading",
            "custom_text",
            "include",
            "page_break_behavior",
            "notes",
        )
        widgets = {
            "custom_text": forms.Textarea(attrs={"rows": 8}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.project = project
        self.fields["volume"].queryset = project.work.volumes.all()
        self.fields["arc"].queryset = project.work.arcs.all()
        self.fields["chapter"].queryset = project.work.chapters.all()
        self.fields["scene"].queryset = project.work.scenes.exclude(lifecycle="trashed")


class PublicationEntryForm(forms.ModelForm):
    class Meta:
        model = PublicationEntry
        fields = (
            "work",
            "volume",
            "arc",
            "chapter",
            "manuscript",
            "export",
            "publication_type",
            "status",
            "platform_label",
            "planned_date",
            "published_date",
            "public_title",
            "public_url",
            "edition",
            "notes",
        )

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.workspace = workspace
        self.fields["work"].queryset = workspace.works.all()
        self.fields["volume"].queryset = workspace.volumes.all()
        self.fields["arc"].queryset = workspace.arcs.all()
        self.fields["chapter"].queryset = workspace.chapters.all()
        self.fields["manuscript"].queryset = workspace.manuscripts.all()
        self.fields["export"].queryset = workspace.exports.filter(status="ready")


class ExportReviewForm(forms.Form):
    export_format = forms.ChoiceField(
        choices=(
            ("text", "Plain text"),
            ("markdown", "Markdown"),
            ("html", "HTML"),
            ("docx", "DOCX"),
            ("pdf", "PDF"),
        )
    )
    filename = forms.CharField(max_length=180)
    lock_revisions = forms.BooleanField(required=False)
    proceed_with_warnings = forms.BooleanField(required=False)


class ArtworkPlacementForm(forms.ModelForm):
    class Meta:
        model = ManuscriptArtworkPlacement
        fields = (
            "artwork",
            "entry",
            "placement",
            "caption",
            "alt_text_override",
            "scaling",
            "page_break_behavior",
            "order",
        )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.project = project
        self.fields["artwork"].queryset = project.workspace.artwork_assets.exclude(
            status="archived"
        )
        self.fields["entry"].queryset = project.entries.all()


class GlossaryEntryForm(forms.ModelForm):
    class Meta:
        model = ManuscriptGlossaryEntry
        fields = ("target_type", "target_id", "display_name", "display_summary", "order")
        widgets = {"display_summary": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.project = project
