from pathlib import Path

from django.urls import reverse

from ai_assistance.tasks import TASKS
from library.services import ALLOWED_ART_EXTENSIONS, ALLOWED_RESEARCH_EXTENSIONS


def test_library_routes_and_private_format_boundaries():
    assert reverse("library-home") == "/library/"
    assert reverse("library-source-list") == "/library/research/"
    assert ".docx" in ALLOWED_RESEARCH_EXTENSIONS
    assert ".pdf" in ALLOWED_RESEARCH_EXTENSIONS
    assert ".png" in ALLOWED_ART_EXTENSIONS


def test_library_ai_tasks_are_real_registered_tools():
    for key in (
        "research_summary",
        "research_compare",
        "research_story",
        "visual_direction",
        "chapter_reference_brief",
    ):
        assert key in TASKS
        assert TASKS[key].output_sections


def test_templates_do_not_expose_storage_paths():
    root = Path(__file__).parents[1] / "templates" / "library"
    content = "\n".join(path.read_text() for path in root.glob("*.html"))
    assert ".path" not in content
    assert "source_file.url" not in content
    assert "artwork.file.url" not in content
    assert "library-artwork-file" in content
