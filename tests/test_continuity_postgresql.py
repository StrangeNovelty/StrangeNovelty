import os

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character
from continuity.models import (
    CharacterKnowledgeRecord,
    PlotThread,
    ReaderKnowledgeRecord,
    Secret,
    ThreadChapterLink,
    ThreadClue,
    ThreadReveal,
)
from scenes.models import Scene
from stories.models import Chapter, Work
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_story(email="continuity@example.invalid"):
    account = Account.objects.create_user(email, password="Synthetic-Continuity-Only!")
    workspace = Workspace.objects.create(name="Synthetic Continuity")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    work = Work.objects.create(workspace=workspace, title="Synthetic Serial", work_type="novel")
    chapter = Chapter.objects.create(workspace=workspace, work=work, title="Threshold", order=1)
    scene = Scene.objects.create(
        workspace=workspace,
        work=work,
        chapter=chapter,
        title="A clue",
        ordering=1,
        structure_order=1,
    )
    character = Character.objects.create(workspace=workspace, name="Synthetic Witness")
    return workspace, client, work, chapter, scene, character


def test_thread_lifecycle_connections_and_workspace_isolation():
    workspace, client, work, chapter, scene, character = setup_story()
    response = client.post(
        reverse("continuity-thread-create"),
        {
            "work": work.id,
            "title": "The sealed promise",
            "thread_type": "promise",
            "status": "open",
            "priority": "critical",
            "visibility": "reader_aware",
            "health": "watch",
        },
    )
    assert response.status_code == 302, response.context["form"].errors
    thread = PlotThread.objects.get(title="The sealed promise")
    link = ThreadChapterLink(thread=thread, chapter=chapter, role="introduced")
    link.full_clean()
    link.save()
    with pytest.raises(IntegrityError):
        ThreadChapterLink.objects.create(thread=thread, chapter=chapter)
    other = Workspace.objects.create(name="Other")
    wrong = Character.objects.create(workspace=other, name="Elsewhere")
    from continuity.models import ThreadCharacterLink

    with pytest.raises(ValidationError):
        ThreadCharacterLink(thread=thread, character=wrong).full_clean()
    assert (
        client.post(
            reverse("continuity-thread-transition", args=(thread.id,)),
            {"status": "resolved", "resolution_notes": "Paid off", "story_time": "Night 3"},
        ).status_code
        == 302
    )
    thread.refresh_from_db()
    assert thread.status == "resolved" and thread.resolution_notes == "Paid off"
    client.post(reverse("continuity-thread-transition", args=(thread.id,)), {"status": "open"})
    thread.refresh_from_db()
    assert thread.status == "open"


def test_clues_reveals_secrets_and_separate_knowledge_layers():
    workspace, client, work, chapter, scene, character = setup_story("knowledge@example.invalid")
    thread = PlotThread.objects.create(
        workspace=workspace, work=work, title="Hidden lineage", status="open"
    )
    clue = ThreadClue.objects.create(
        thread=thread,
        title="Broken crest",
        description="A synthetic mark",
        status="planted",
        subtlety="subtle",
        chapter=chapter,
        scene=scene,
    )
    reveal = ThreadReveal.objects.create(
        thread=thread,
        title="The name",
        description="Synthetic disclosure",
        status="revealed",
        chapter=chapter,
        scene=scene,
    )
    secret = Secret.objects.create(
        workspace=workspace,
        work=work,
        thread=thread,
        title="A hidden name",
        truth_statement="Synthetic truth",
        public_belief="Synthetic misconception",
    )
    ReaderKnowledgeRecord.objects.create(
        workspace=workspace,
        work=work,
        secret=secret,
        subject_type="secret",
        title="Reader belief",
        knowledge_statement="A false version",
        certainty="false_belief",
        chapter=chapter,
    )
    CharacterKnowledgeRecord.objects.create(
        workspace=workspace,
        work=work,
        character=character,
        secret=secret,
        knowledge_statement="The true version",
        knowledge_state="knows",
        certainty="certain",
        chapter=chapter,
    )
    page = client.get(reverse("continuity-secret-detail", args=(secret.id,)))
    assert page.status_code == 200 and b"Knowledge Matrix" in page.content
    overview = client.get(reverse("continuity-home"))
    assert overview.status_code == 200 and clue.title.encode() in overview.content
    assert reveal.thread_id == thread.id


def test_panels_search_and_post_only_transitions():
    workspace, client, work, chapter, scene, character = setup_story("panels@example.invalid")
    thread = PlotThread.objects.create(
        workspace=workspace,
        work=work,
        title="Searchable oath",
        short_summary="Unresolved synthetic promise",
    )
    ThreadChapterLink.objects.create(thread=thread, chapter=chapter, role="introduced")
    assert (
        b"Searchable oath"
        in client.get(reverse("chapter-detail", args=(work.id, chapter.id))).content
    )
    assert (
        b"Searchable oath"
        in client.post(reverse("scene-search"), {"query": "synthetic promise"}).content
    )
    assert client.get(reverse("continuity-thread-transition", args=(thread.id,))).status_code == 405
    other_account = Account.objects.create_user(
        "outsider@example.invalid", password="Synthetic-Only!"
    )
    other_client = Client()
    other_client.force_login(other_account)
    assert (
        other_client.get(reverse("continuity-thread-detail", args=(thread.id,))).status_code == 404
    )
