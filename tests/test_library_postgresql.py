import os
import struct
import tempfile
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import Account
from library.models import (
    ArtworkAsset,
    CollectionMembership,
    LibraryCollection,
    LibraryConnection,
    ResearchNote,
    ResearchSource,
)
from library.search import search_library
from stories.models import Work
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="PostgreSQL required"),
]


def setup_library():
    account = Account.objects.create_user(
        f"library-{uuid.uuid4()}@example.invalid", "Synthetic-Only-Password!"
    )
    workspace = Workspace.objects.create(name="Synthetic Library")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    return account, workspace, client


def png_upload(name="synthetic.png"):
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 3, 2) + b"\x00" * 8
    return SimpleUploadedFile(name, data, content_type="image/png")


def test_url_file_and_citation_sources_extraction_and_duplicate_checksum():
    _, workspace, client = setup_library()
    url_only = ResearchSource.objects.create(
        workspace=workspace,
        title="Synthetic Website",
        source_type="website",
        url="https://example.invalid",
    )
    ResearchSource.objects.create(
        workspace=workspace, title="Synthetic Citation", citation="Invented Author. Invented Work."
    )
    with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
        response = client.post(
            reverse("library-source-create"),
            {
                "title": "Synthetic Notes",
                "source_type": "reference_document",
                "status": "reviewing",
                "source_file": SimpleUploadedFile(
                    "notes.txt", b"Synthetic searchable detail.", content_type="text/plain"
                ),
                "extract_now": "on",
            },
        )
        assert response.status_code == 302
        source = ResearchSource.objects.exclude(id=url_only.id).get(title="Synthetic Notes")
        assert source.extracted_text_status == "extracted"
        assert source.extracted_text == "Synthetic searchable detail."
        assert source.checksum and source.source_file.name.startswith(
            f"library/{workspace.id}/research/"
        )
        duplicate = client.post(
            reverse("library-source-create"),
            {
                "title": "Duplicate",
                "source_type": "other",
                "status": "unread",
                "source_file": SimpleUploadedFile("copy.txt", b"Synthetic searchable detail."),
            },
        )
        assert duplicate.status_code == 200
        assert b"already in the Library" in duplicate.content


def test_artwork_private_delivery_dimensions_and_workspace_isolation():
    _, workspace, client = setup_library()
    with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
        response = client.post(
            reverse("library-artwork-create"),
            {
                "title": "Synthetic Portrait",
                "artwork_type": "character_portrait",
                "status": "reference",
                "file": png_upload(),
                "alt_text": "A synthetic geometric portrait",
            },
        )
        assert response.status_code == 302
        artwork = ArtworkAsset.objects.get(workspace=workspace)
        assert (artwork.width, artwork.height) == (3, 2)
        assert artwork.original_filename == "synthetic.png"
        assert client.get(reverse("library-artwork-file", args=(artwork.id,))).status_code == 200
        assert Client().get(reverse("library-artwork-file", args=(artwork.id,))).status_code == 302


def test_notes_mixed_collections_connections_search_and_dashboard():
    _, workspace, client = setup_library()
    source = ResearchSource.objects.create(workspace=workspace, title="Synthetic Source")
    note = ResearchNote.objects.create(
        workspace=workspace,
        source=source,
        title="Synthetic Note",
        note_content="Observed source material",
        interpretation="Author interpretation",
        story_application="Possible story use",
    )
    collection = LibraryCollection.objects.create(
        workspace=workspace, name="Synthetic Mood Board", collection_type="mood_board"
    )
    member = CollectionMembership(collection=collection, note=note, order=1)
    member.full_clean()
    member.save()
    duplicate = CollectionMembership(collection=collection, note=note, order=2)
    with pytest.raises(ValidationError):
        duplicate.full_clean(validate_constraints=True)
    work = Work.objects.create(workspace=workspace, title="Synthetic Work", work_type="novel")
    link = LibraryConnection(workspace=workspace, note=note, work=work, role="inspiration")
    link.full_clean()
    link.save()
    other = Workspace.objects.create(name="Other")
    wrong = LibraryConnection(workspace=other, note=note, work=work)
    with pytest.raises(ValidationError):
        wrong.full_clean()
    account = workspace.grants.get(role="owner").account
    results = search_library(actor=account, workspace_id=workspace.id, query_text="interpretation")
    assert results["research_note_results"][0].record == note
    home = client.get(reverse("library-home"))
    assert home.status_code == 200 and b"Synthetic Mood Board" in home.content
    dashboard = client.get(reverse("workspace-home"))
    assert dashboard.status_code == 200 and b"Library" in dashboard.content


def test_status_mutation_is_post_only():
    _, workspace, client = setup_library()
    source = ResearchSource.objects.create(workspace=workspace, title="Synthetic Source")
    url = reverse("library-transition", args=("source", source.id))
    assert client.get(url).status_code == 405
    assert client.post(url, {"status": "archived"}).status_code == 302
    source.refresh_from_db()
    assert source.status == "archived"
