import os

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character, CharacterScene
from scenes.models import Scene
from scenes.services import create_scene, revise_scene_content
from stories.models import Chapter, Work
from stories.search import search_chapters
from stories.services import update_scene_placement
from stories.writing import summarize_chapter
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

PASSWORD = "Synthetic-Chapter-Workspace-Only!"


def _owner(email: str = "chapter-workspace@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic Chapter Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace,
        account=account,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _client(account: Account) -> Client:
    client = Client()
    client.force_login(account)
    return client


def _chapter(workspace: Workspace, **values: object) -> Chapter:
    work = Work.objects.create(
        workspace=workspace,
        title=str(values.pop("work_title", "Synthetic Work")),
        work_type=Work.WorkType.NOVEL,
        status=Work.Status.DRAFTING,
    )
    return Chapter.objects.create(
        workspace=workspace,
        work=work,
        title="Opening Movement",
        order=1024,
        **values,
    )


def _scene(account: Account, chapter: Chapter, title: str, content: str, order: int) -> Scene:
    result = create_scene(actor=account, workspace_id=chapter.workspace_id, title=title)
    if content:
        result = revise_scene_content(
            actor=account,
            workspace_id=chapter.workspace_id,
            scene_id=result.scene.id,
            expected_current_revision_id=result.revision.id,
            expected_scene_version=result.scene.version,
            proposed_content=content,
        )
    update_scene_placement(
        actor=account,
        workspace_id=chapter.workspace_id,
        scene_id=result.scene.id,
        values={
            "work": chapter.work,
            "volume": chapter.volume,
            "arc": chapter.arc,
            "chapter": chapter,
            "structure_order": order,
        },
    )
    result.scene.refresh_from_db()
    return result.scene


def _chapter_payload(chapter: Chapter, **changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "volume": chapter.volume_id or "",
        "arc": chapter.arc_id or "",
        "title": chapter.title,
        "label": chapter.label,
        "order": chapter.order,
        "status": chapter.status,
        "summary": chapter.summary,
        "concept": chapter.concept,
        "goal": chapter.goal,
        "key_beats": chapter.key_beats,
        "emotional_arc": chapter.emotional_arc,
        "character_focus": chapter.character_focus,
        "brain_dump": chapter.brain_dump,
        "outline": chapter.outline,
        "pov_character": chapter.pov_character_id or "",
        "notes": chapter.notes,
    }
    payload.update(changes)
    return payload


def test_planning_fields_edit_empty_states_status_and_search() -> None:
    account, workspace = _owner()
    chapter = _chapter(workspace)
    client = _client(account)
    url = reverse("chapter-detail", kwargs={"work_id": chapter.work_id, "chapter_id": chapter.id})
    empty = client.get(url)
    assert empty.status_code == 200
    assert b"Intake" in empty.content and b"Begin with the first Scene" in empty.content
    long_material = "unbroken-fragment-" * 120
    response = client.post(
        url,
        _chapter_payload(
            chapter,
            status=Chapter.Status.REVISING,
            concept="A lighthouse answers a forbidden signal.",
            goal="Force the keeper to choose.",
            key_beats="Signal\nRefusal\nAnswer",
            emotional_arc="Certainty to dread",
            character_focus="The keeper drives the choice.",
            brain_dump=f"Salt dialogue fragment and unresolved bell question. {long_material}",
            outline="1. Signal\n2. Choice\n3. Consequence",
            notes="Keep the ending quiet.",
        ),
    )
    assert response.status_code == 303
    chapter.refresh_from_db()
    assert chapter.status == Chapter.Status.REVISING
    assert long_material in chapter.brain_dump
    assert long_material.encode() in client.get(url).content
    for query in ("forbidden signal", "keeper drives", "unresolved bell", "Consequence"):
        assert [
            item.chapter
            for item in search_chapters(actor=account, workspace_id=workspace.id, query_text=query)
        ] == [chapter]


def test_derived_words_reading_time_recent_scene_and_trashed_exclusion() -> None:
    account, workspace = _owner()
    chapter = _chapter(workspace)
    first = _scene(account, chapter, "First", "one two three", 1024)
    second = _scene(account, chapter, "Second", "word " * 250, 2048)
    trashed = _scene(account, chapter, "Discarded", "hidden " * 500, 3072)
    Scene.objects.filter(id=trashed.id).update(lifecycle=Scene.Lifecycle.TRASHED)
    summary = summarize_chapter(chapter)
    assert summary.scene_count == 2
    assert summary.word_count == 253
    assert summary.reading_minutes == 2
    assert summary.recent_scene == second
    assert first in [item.scene for item in summary.scenes]
    response = _client(account).get(
        reverse("chapter-detail", kwargs={"work_id": chapter.work_id, "chapter_id": chapter.id})
    )
    assert b"Latest revision" in response.content


def test_cast_is_derived_unique_and_pov_is_distinguished() -> None:
    account, workspace = _owner()
    pov = Character.objects.create(workspace=workspace, name="Synthetic POV")
    companion = Character.objects.create(workspace=workspace, name="Synthetic Companion")
    chapter = _chapter(workspace, pov_character=pov)
    first = _scene(account, chapter, "First", "brief scene", 1024)
    second = _scene(account, chapter, "Second", "another scene", 2048)
    discarded = _scene(account, chapter, "Discarded", "unused scene", 3072)
    discarded_character = Character.objects.create(workspace=workspace, name="Discarded Character")
    for scene, character in ((first, pov), (first, companion), (second, companion)):
        CharacterScene.objects.create(workspace=workspace, scene=scene, character=character)
    CharacterScene.objects.create(
        workspace=workspace,
        scene=discarded,
        character=discarded_character,
    )
    Scene.objects.filter(id=discarded.id).update(lifecycle=Scene.Lifecycle.TRASHED)
    summary = summarize_chapter(chapter)
    assert summary.cast == (companion, pov)
    response = _client(account).get(
        reverse("chapter-detail", kwargs={"work_id": chapter.work_id, "chapter_id": chapter.id})
    )
    assert response.content.count(companion.name.encode()) >= 1
    assert b"POV" in response.content


def test_scene_reorder_detach_are_post_only_scoped_and_archived_read_only() -> None:
    account, workspace = _owner()
    chapter = _chapter(workspace)
    scene = _scene(account, chapter, "Movable", "words", 1024)
    client = _client(account)
    kwargs = {"work_id": chapter.work_id, "chapter_id": chapter.id, "scene_id": scene.id}
    order_url = reverse("chapter-scene-order", kwargs=kwargs)
    detach_url = reverse("chapter-scene-detach", kwargs=kwargs)
    assert client.get(order_url).status_code == 405
    assert client.post(order_url, {"structure_order": 4096}).status_code == 303
    scene.refresh_from_db()
    assert scene.structure_order == 4096
    assert client.post(detach_url).status_code == 303
    scene.refresh_from_db()
    assert scene.chapter is None and scene.work == chapter.work
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        values={
            "work": chapter.work,
            "chapter": chapter,
            "volume": None,
            "arc": None,
            "structure_order": 1024,
        },
    )
    Scene.objects.filter(id=scene.id).update(lifecycle=Scene.Lifecycle.ARCHIVED)
    assert client.post(detach_url).status_code == 404


def test_work_cards_dashboard_and_workspace_isolation() -> None:
    account, workspace = _owner()
    chapter = _chapter(workspace, status=Chapter.Status.DRAFTING, outline="A working outline")
    _scene(account, chapter, "Writing now", "one two three four", 1024)
    client = _client(account)
    work_response = client.get(reverse("work-detail", kwargs={"work_id": chapter.work_id}))
    assert b"1 Scenes" in work_response.content
    assert b"4 words" in work_response.content
    dashboard = client.get(reverse("workspace-home"))
    assert chapter.title.encode() in dashboard.content
    assert b"Continue Chapter" in dashboard.content
    other_account, other_workspace = _owner("other-chapter@example.invalid")
    other = _chapter(other_workspace, concept="Private other concept")
    assert (
        search_chapters(
            actor=account, workspace_id=workspace.id, query_text="Private other concept"
        )
        == []
    )
    assert (
        _client(account)
        .get(reverse("chapter-detail", kwargs={"work_id": other.work_id, "chapter_id": other.id}))
        .status_code
        == 404
    )
    assert other_account != account
