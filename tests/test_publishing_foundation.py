from pathlib import Path

from django.urls import reverse

from ai_assistance.tasks import TASKS
from publishing.exporting import MIMES
from publishing.profiles import PROFILES


def test_publishing_routes_profiles_and_formats_are_bounded():
    assert reverse("publishing-home") == "/publishing/"
    assert reverse("publishing-manuscript-list") == "/publishing/manuscripts/"
    assert set(MIMES) == {"text", "markdown", "html", "docx", "pdf"}
    for key in (
        "clean_manuscript",
        "web_serial",
        "novella",
        "standard_novel",
        "screenplay",
        "comic_script",
        "simple_archive",
        "custom",
    ):
        assert key in PROFILES
        assert PROFILES[key].version == "publishing-profile-v1"


def test_publication_ai_tasks_are_reviewed_product_tasks():
    for key in (
        "manuscript_summary",
        "manuscript_back_cover",
        "manuscript_synopsis",
        "submission_summary",
        "publication_readiness",
        "compilation_consistency",
    ):
        assert key in TASKS
        assert TASKS[key].category == "publication"


def test_publishing_templates_hide_private_storage_paths():
    root = Path(__file__).parents[1] / "templates" / "publishing"
    content = "\n".join(path.read_text() for path in root.glob("*.html"))
    assert ".path" not in content
    assert ".file.url" not in content
    assert "publishing-export-download" in content
    assert "window.print" in content
