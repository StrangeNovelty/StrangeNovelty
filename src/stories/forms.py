from typing import cast

from django import forms

from characters.models import Character
from scenes.models import Scene
from stories.models import Arc, Chapter, Volume, Work
from workspaces.models import Workspace


class WorkForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = (
            "title",
            "subtitle",
            "work_type",
            "status",
            "premise",
            "description",
            "intended_audience",
            "genre_notes",
        )
        labels = {
            "work_type": "Work type",
            "premise": "Short premise or summary",
            "description": "Description or working notes",
            "intended_audience": "Intended audience",
            "genre_notes": "Genre notes",
        }
        help_texts = {
            "work_type": "Choose the closest format; this does not impose a hierarchy.",
            "status": "The current creative phase for this Work.",
        }
        widgets = {
            "premise": forms.Textarea(attrs={"rows": 4}),
            "description": forms.Textarea(attrs={"rows": 6}),
            "genre_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_title(self) -> str:
        title = cast(str, self.cleaned_data["title"]).strip()
        if not title:
            raise forms.ValidationError("Work title is required.")
        return title


class WorkSearchForm(forms.Form):
    query = forms.CharField(max_length=200, strip=True, label="Search Works")


class OrderedStructureForm(forms.ModelForm):
    def __init__(self, *args: object, creating: bool = False, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["order"].required = not creating
        self.fields["order"].help_text = (
            "Leave blank to place this item after the current structure."
            if creating
            else "Lower numbers appear earlier in the Work."
        )

    def clean_title(self) -> str:
        title = cast(str, self.cleaned_data["title"]).strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        return title


class VolumeForm(OrderedStructureForm):
    class Meta:
        model = Volume
        fields = ("title", "order", "status", "summary", "notes")
        labels = {"order": "Volume order"}
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class ArcForm(OrderedStructureForm):
    class Meta:
        model = Arc
        fields = ("volume", "title", "order", "status", "summary", "purpose", "notes")
        labels = {
            "volume": "Volume (optional)",
            "order": "Arc order",
            "purpose": "Goals or purpose",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4}),
            "purpose": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        work: Work,
        creating: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, creating=creating, **kwargs)
        self.instance.workspace = workspace
        self.instance.work = work
        self.fields["volume"].queryset = Volume.objects.filter(workspace=workspace, work=work)


class ChapterForm(OrderedStructureForm):
    class Meta:
        model = Chapter
        fields = (
            "volume",
            "arc",
            "title",
            "label",
            "order",
            "status",
            "summary",
            "pov_character",
            "notes",
        )
        labels = {
            "volume": "Volume (optional)",
            "arc": "Arc (optional)",
            "label": "Chapter number or author-defined label",
            "order": "Chapter order",
            "summary": "Summary or chapter goal",
            "pov_character": "POV Character (optional)",
        }
        help_texts = {
            "label": "Examples: Chapter 4, Act II, Interlude, or Sequence A.",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 5}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        work: Work,
        creating: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, creating=creating, **kwargs)
        self.instance.workspace = workspace
        self.instance.work = work
        self.fields["volume"].queryset = Volume.objects.filter(workspace=workspace, work=work)
        self.fields["arc"].queryset = Arc.objects.filter(workspace=workspace, work=work)
        self.fields["pov_character"].queryset = Character.objects.filter(workspace=workspace)

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        volume = cleaned.get("volume")
        arc = cleaned.get("arc")
        if (
            isinstance(arc, Arc)
            and arc.volume_id
            and (not isinstance(volume, Volume) or volume.id != arc.volume_id)
        ):
            self.add_error("volume", "Select the Volume that contains this Arc.")
        return cleaned


class _PlacementChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj: object) -> str:
        if isinstance(obj, (Volume, Arc, Chapter)):
            return f"{obj.work.title} — {obj}"
        return str(obj)


class ScenePlacementForm(forms.Form):
    work = forms.ModelChoiceField(
        queryset=Work.objects.none(), required=False, empty_label="Unassigned"
    )
    volume = _PlacementChoiceField(
        queryset=Volume.objects.none(), required=False, empty_label="No Volume"
    )
    arc = _PlacementChoiceField(queryset=Arc.objects.none(), required=False, empty_label="No Arc")
    chapter = _PlacementChoiceField(
        queryset=Chapter.objects.none(), required=False, empty_label="No Chapter"
    )
    structure_order = forms.IntegerField(
        required=False,
        min_value=0,
        label="Scene order",
        help_text="Leave blank to place the Scene after others in the same context.",
    )

    def __init__(
        self,
        *args: object,
        workspace: Workspace,
        scene: Scene,
        **kwargs: object,
    ) -> None:
        if not args and "initial" not in kwargs:
            kwargs["initial"] = {
                "work": scene.work,
                "volume": scene.volume,
                "arc": scene.arc,
                "chapter": scene.chapter,
                "structure_order": scene.structure_order,
            }
        super().__init__(*args, **kwargs)
        self.fields["work"].queryset = Work.objects.filter(workspace=workspace)
        self.fields["volume"].queryset = Volume.objects.filter(workspace=workspace)
        self.fields["arc"].queryset = Arc.objects.filter(workspace=workspace)
        self.fields["chapter"].queryset = Chapter.objects.filter(workspace=workspace)

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        work = cleaned.get("work")
        volume = cleaned.get("volume")
        arc = cleaned.get("arc")
        chapter = cleaned.get("chapter")
        if work is None:
            if volume or arc or chapter:
                self.add_error("work", "Select a Work before choosing structure levels.")
            cleaned["structure_order"] = None
            return cleaned
        if isinstance(volume, Volume) and volume.work_id != work.id:
            self.add_error("volume", "Volume must belong to the selected Work.")
        if isinstance(arc, Arc):
            if arc.work_id != work.id:
                self.add_error("arc", "Arc must belong to the selected Work.")
            if arc.volume_id and (not isinstance(volume, Volume) or volume.id != arc.volume_id):
                self.add_error("volume", "Volume must match the selected Arc.")
        if isinstance(chapter, Chapter):
            if chapter.work_id != work.id:
                self.add_error("chapter", "Chapter must belong to the selected Work.")
            if chapter.volume_id and (
                not isinstance(volume, Volume) or volume.id != chapter.volume_id
            ):
                self.add_error("volume", "Volume must match the selected Chapter.")
            if chapter.arc_id and (not isinstance(arc, Arc) or arc.id != chapter.arc_id):
                self.add_error("arc", "Arc must match the selected Chapter.")
        return cleaned


class ChapterSceneCreateForm(forms.Form):
    title = forms.CharField(max_length=200, strip=True, label="Scene title")


class ChapterSceneAttachForm(forms.Form):
    scene = forms.ModelChoiceField(
        queryset=Scene.objects.none(),
        empty_label="Choose an unassigned Scene",
        label="Existing Scene",
    )

    def __init__(self, *args: object, workspace: Workspace, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["scene"].queryset = Scene.objects.filter(
            workspace=workspace,
            work__isnull=True,
            lifecycle=Scene.Lifecycle.ACTIVE,
        ).order_by("ordering", "id")
