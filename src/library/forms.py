from django import forms

from library.models import (
    ArtworkAsset,
    CollectionMembership,
    LibraryCollection,
    ResearchNote,
    ResearchSource,
)
from library.services import inspect_upload


class SourceForm(forms.ModelForm):
    extract_now = forms.BooleanField(required=False, label="Extract readable text after upload")

    class Meta:
        model = ResearchSource
        fields = (
            "title",
            "source_type",
            "status",
            "creator",
            "publisher",
            "publication_date_text",
            "url",
            "accessed_date",
            "citation",
            "short_summary",
            "relevance",
            "credibility_notes",
            "bias_notes",
            "usage_rights_notes",
            "tags",
            "source_file",
        )

    def clean_source_file(self):
        upload = self.cleaned_data.get("source_file")
        if upload and not getattr(upload, "_committed", False):
            self.upload_metadata = inspect_upload(upload)
        return upload


class NoteForm(forms.ModelForm):
    class Meta:
        model = ResearchNote
        fields = (
            "source",
            "title",
            "note_type",
            "status",
            "summary",
            "note_content",
            "quotation_excerpt",
            "page_reference",
            "interpretation",
            "story_application",
            "questions",
            "tags",
        )
        widgets = {
            name: forms.Textarea(attrs={"rows": 4})
            for name in (
                "summary",
                "note_content",
                "quotation_excerpt",
                "interpretation",
                "story_application",
                "questions",
            )
        }

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = workspace.research_sources.all()
        self.instance.workspace = workspace


class ArtworkForm(forms.ModelForm):
    class Meta:
        model = ArtworkAsset
        fields = (
            "title",
            "artwork_type",
            "status",
            "description",
            "creator_source",
            "source_url",
            "usage_rights_notes",
            "file",
            "alt_text",
            "visual_notes",
            "palette_notes",
            "mood",
            "tags",
            "is_primary",
        )

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if upload and not getattr(upload, "_committed", False):
            self.upload_metadata = inspect_upload(upload, artwork=True)
        return upload


class CollectionForm(forms.ModelForm):
    class Meta:
        model = LibraryCollection
        fields = ("name", "collection_type", "status", "description", "work", "order")

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work"].queryset = workspace.works.all()
        self.instance.workspace = workspace


class MembershipForm(forms.ModelForm):
    class Meta:
        model = CollectionMembership
        fields = ("source", "note", "artwork", "order", "caption", "notes", "pinned")

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = workspace.research_sources.all()
        self.fields["note"].queryset = workspace.research_notes.all()
        self.fields["artwork"].queryset = workspace.artwork_assets.all()
