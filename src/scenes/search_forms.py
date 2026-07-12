from django import forms

from scenes.search import MAX_SEARCH_QUERY_CHARACTERS


class SceneSearchForm(forms.Form):
    query = forms.CharField(max_length=MAX_SEARCH_QUERY_CHARACTERS, strip=True, label="Search")
    include_archived = forms.BooleanField(required=False, label="Include archived Scenes")
