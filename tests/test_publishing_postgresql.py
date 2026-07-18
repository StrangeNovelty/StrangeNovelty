import os
import tempfile
import uuid
import zipfile
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import Account
from characters.models import Character
from jobs.services import claim_jobs, execute_claim
from publishing.compilation import compile_manuscript, populate_from_work, use_latest_revisions
from publishing.exporting import generate_export
from publishing.models import (
    ExportRecord,
    ManuscriptArtworkPlacement,
    ManuscriptEntry,
    ManuscriptGlossaryEntry,
    ManuscriptProject,
    PublicationEntry,
)
from publishing.search import search_publishing
from scenes.services import create_scene, revise_scene_content
from stories.models import Chapter, Work
from stories.services import update_scene_placement
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="PostgreSQL required"),
]


def setup_story():
    account = Account.objects.create_user(
        f"publishing-{uuid.uuid4()}@example.invalid", "Synthetic-Only-Password!"
    )
    workspace = Workspace.objects.create(name="Synthetic Publishing Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Manuscript", work_type="web_serial"
    )
    chapter = Chapter.objects.create(
        workspace=workspace,
        work=work,
        title="Synthetic Chapter",
        label="Episode One",
        order=10,
    )
    result = create_scene(actor=account, workspace_id=workspace.id, title="Synthetic Scene")
    revised = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=result.scene.id,
        expected_current_revision_id=result.revision.id,
        expected_scene_version=result.scene.version,
        proposed_content="First synthetic paragraph.\n\nSecond synthetic paragraph.",
    )
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=revised.scene.id,
        values={
            "work": work,
            "volume": None,
            "arc": None,
            "chapter": chapter,
            "structure_order": 10,
        },
    )
    revised.scene.refresh_from_db()
    client = Client()
    client.force_login(account)
    return account, workspace, work, chapter, revised.scene, client


def project_for(workspace, work):
    project = ManuscriptProject.objects.create(
        workspace=workspace,
        work=work,
        name="Synthetic Reading Copy",
        manuscript_type="web_serial_reading_copy",
        title_override="Synthetic Export Title",
        author_name_override="Synthetic Author",
        formatting_profile="web_serial",
    )
    populate_from_work(project)
    return project


def test_project_population_compilation_order_selection_and_scope():
    _, workspace, work, chapter, scene, _ = setup_story()
    project = project_for(workspace, work)
    assert list(project.entries.values_list("entry_type", flat=True)) == [
        "title_page",
        "chapter",
        "scene",
    ]
    compiled = compile_manuscript(project)
    assert compiled.title == "Synthetic Export Title"
    assert compiled.word_count == 8
    assert compiled.chapter_count == compiled.scene_count == 1
    assert compiled.sections[-1].paragraphs == (
        "First synthetic paragraph.",
        "Second synthetic paragraph.",
    )
    assert compiled.checksum == compile_manuscript(project).checksum
    selection = project.entries.get(entry_type="scene").scene_selection
    assert selection.selected_revision_id == scene.current_revision_id
    other = Workspace.objects.create(name="Other")
    wrong = ManuscriptProject(workspace=other, work=work, name="Wrong")
    with pytest.raises(ValidationError):
        wrong.full_clean()
    duplicate = ManuscriptEntry(project=project, order=10, entry_type="custom_prose")
    with pytest.raises(ValidationError):
        duplicate.full_clean(validate_constraints=True)


def test_revision_staleness_latest_and_lock_preserve_provenance():
    account, workspace, work, _, scene, _ = setup_story()
    project = project_for(workspace, work)
    selected = project.entries.get(entry_type="scene").scene_selection.selected_revision_id
    result = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="A newer synthetic Revision.",
    )
    scene.refresh_from_db()
    selection = project.entries.get(entry_type="scene").scene_selection
    assert selection.selected_revision_id == selected and selection.is_stale
    assert any("Newer Revision" in warning for warning in compile_manuscript(project).warnings)
    use_latest_revisions(project, lock=True)
    selection.refresh_from_db()
    assert selection.selected_revision_id == result.revision.id
    assert selection.locked and selection.selection_mode == "locked"


def test_all_export_formats_content_private_download_and_history():
    _, workspace, work, _, _, client = setup_story()
    project = project_for(workspace, work)
    with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
        payloads = {}
        for export_format in ("text", "markdown", "html", "docx", "pdf"):
            record = ExportRecord.objects.create(
                workspace=workspace,
                project=project,
                export_format=export_format,
                filename=f"synthetic.{export_format}",
            )
            generate_export(record.id)
            record.refresh_from_db()
            assert record.status == "ready" and record.checksum and record.file_size
            assert record.file.name.startswith(f"publishing/{workspace.id}/")
            with record.file.open("rb") as handle:
                payloads[export_format] = handle.read()
            response = client.get(reverse("publishing-export-download", args=(record.id,)))
            assert response.status_code == 200
            assert (
                Client().get(reverse("publishing-export-download", args=(record.id,))).status_code
                == 302
            )
        assert b"First synthetic paragraph" in payloads["text"]
        assert b"# Synthetic Export Title" in payloads["markdown"]
        assert b"<!doctype html>" in payloads["html"]
        assert b"&lt;script" not in payloads["html"]
        assert payloads["docx"].startswith(b"PK")
        with zipfile.ZipFile(BytesIO(payloads["docx"])) as archive:
            document_xml = archive.read("word/document.xml")
            assert b"First synthetic paragraph" in document_xml
        assert payloads["pdf"].startswith(b"%PDF")
        history = client.get(reverse("publishing-export-list"))
        assert history.status_code == 200 and b"synthetic-" in history.content


def test_export_review_queues_job_and_worker_generates_idempotently():
    _, workspace, work, _, _, client = setup_story()
    project = project_for(workspace, work)
    with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
        response = client.post(
            reverse("publishing-export-review", args=(project.id,)),
            {
                "export_format": "html",
                "filename": "synthetic-reading-copy",
                "lock_revisions": "on",
                "proceed_with_warnings": "on",
            },
        )
        assert response.status_code == 302
        export = ExportRecord.objects.get(workspace=workspace)
        assert export.status == "queued" and export.job.target_id == export.id
        claimed_jobs = claim_jobs(worker_id="synthetic-worker", batch_size=20)
        job = None
        for claimed in claimed_jobs:
            completed = execute_claim(claimed)
            if completed.id == export.job_id:
                job = completed
        export.refresh_from_db()
        assert job is not None and job.state == "succeeded" and export.status == "ready"
        assert export.source_snapshot["revision_ids"]


def test_reading_preview_publication_change_search_dashboard_and_post_only():
    account, workspace, work, chapter, scene, client = setup_story()
    project = project_for(workspace, work)
    preview = client.get(reverse("publishing-reading-preview", args=(project.id,)))
    assert preview.status_code == 200
    assert b"First synthetic paragraph" in preview.content and b"window.print" in preview.content
    publication = PublicationEntry.objects.create(
        workspace=workspace,
        work=work,
        chapter=chapter,
        publication_type="web_serial_chapter",
        public_title="Synthetic Episode",
    )
    transition = reverse("publishing-publication-transition", args=(publication.id,))
    assert client.get(transition).status_code == 405
    assert client.post(transition, {"status": "published"}).status_code == 302
    publication.refresh_from_db()
    assert publication.published_date and not publication.source_changed_after_publication
    revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="Changed after publication.",
    )
    publication.refresh_from_db()
    assert publication.source_changed_after_publication
    results = search_publishing(
        actor=account, workspace_id=workspace.id, query_text="Synthetic Reading"
    )
    assert results["manuscript_results"][0].record == project
    project.status = "ready"
    project.save()
    dashboard = client.get(reverse("workspace-home"))
    assert dashboard.status_code == 200 and b"Manuscripts awaiting review" in dashboard.content


def test_explicit_glossary_selection_and_missing_artwork_warning():
    _, workspace, work, _, _, _ = setup_story()
    project = project_for(workspace, work)
    character = Character.objects.create(workspace=workspace, name="Synthetic Glossary Person")
    glossary = ManuscriptGlossaryEntry(
        project=project,
        target_type="character",
        target_id=character.id,
        display_name="Glossary Person",
        display_summary="Public synthetic glossary summary only.",
    )
    glossary.full_clean()
    glossary.save()
    ManuscriptEntry.objects.create(
        project=project, order=1000, entry_type="glossary", custom_heading="Glossary"
    )
    from library.models import ArtworkAsset

    artwork = ArtworkAsset.objects.create(
        workspace=workspace,
        title="Missing Synthetic Cover",
        artwork_type="cover_concept",
        file="library/missing/synthetic.png",
        original_filename="synthetic.png",
        mime_type="image/png",
        size=10,
        checksum="a" * 64,
    )
    placement = ManuscriptArtworkPlacement(project=project, artwork=artwork, placement="cover")
    placement.full_clean()
    placement.save()
    compiled = compile_manuscript(project)
    assert any("Artwork file unavailable" in warning for warning in compiled.warnings)
    assert any(
        "Public synthetic glossary summary" in paragraph
        for section in compiled.sections
        for paragraph in section.paragraphs
    )
