import os
import re
from typing import cast

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character
from scenes.models import Scene
from scenes.services import create_scene
from stories.models import Arc, Chapter, Volume, Work
from stories.search import search_chapters, search_works
from stories.services import (
    StoryStructureConflict,
    create_arc,
    create_chapter,
    create_volume,
    update_scene_placement,
)
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"),
        reason="TEST_DATABASE_URL is required for PostgreSQL integration tests.",
    ),
]

TEST_PASSWORD = "Synthetic-Story-Structure-Only!"


def _owner(email: str = "story-structure-owner@example.invalid") -> tuple[Account, Workspace]:
    account = Account.objects.create_user(email, password=TEST_PASSWORD)
    workspace = cast(Workspace, Workspace.objects.create(name="Synthetic Story Structure"))
    WorkspaceGrant.objects.create(
        account=account,
        workspace=workspace,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    return account, workspace


def _client(account: Account) -> Client:
    client = Client()
    client.force_login(account)
    return client


def _work(workspace: Workspace, title: str = "The Lantern Coast", **values: str) -> Work:
    defaults = {
        "subtitle": "A synthetic serial",
        "work_type": Work.WorkType.WEB_SERIAL,
        "status": Work.Status.DRAFTING,
        "premise": "A keeper crosses a test-only coast.",
        "description": "Synthetic working notes.",
        "intended_audience": "Adult speculative readers",
        "genre_notes": "Literary fantasy",
    }
    defaults.update(values)
    return cast(Work, Work.objects.create(workspace=workspace, title=title, **defaults))


def _work_payload(**overrides: str) -> dict[str, str]:
    payload = {
        "title": "The Lantern Coast",
        "subtitle": "A synthetic serial",
        "work_type": "web_serial",
        "status": "drafting",
        "premise": "A keeper crosses a test-only coast.",
        "description": "Synthetic working notes.",
        "intended_audience": "Adult speculative readers",
        "genre_notes": "Literary fantasy",
    }
    payload.update(overrides)
    return payload


def _volume_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Volume One",
        "order": "",
        "status": "active",
        "summary": "The first movement.",
        "notes": "Synthetic Volume notes.",
    }
    payload.update(overrides)
    return payload


def _arc_payload(volume: Volume | None = None, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "volume": volume.id if volume else "",
        "title": "The Harbor Arc",
        "order": "",
        "status": "active",
        "summary": "A bounded synthetic Arc.",
        "purpose": "Move the keeper toward the harbor.",
        "notes": "Synthetic Arc notes.",
    }
    payload.update(overrides)
    return payload


def _chapter_payload(
    volume: Volume | None = None,
    arc: Arc | None = None,
    character: Character | None = None,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "volume": volume.id if volume else "",
        "arc": arc.id if arc else "",
        "title": "A Door in the Fog",
        "label": "Episode 1",
        "order": "",
        "status": "drafting",
        "summary": "The keeper finds a door.",
        "pov_character": character.id if character else "",
        "notes": "Synthetic Chapter notes.",
    }
    payload.update(overrides)
    return payload


def test_work_library_creation_edit_search_and_empty_state() -> None:
    account, workspace = _owner()
    client = _client(account)
    list_url = reverse("work-list")
    empty = client.get(list_url)
    assert empty.status_code == 200
    assert b"No Works yet" in empty.content
    assert "no-store" in empty.headers["Cache-Control"]

    created = client.post(reverse("work-create"), _work_payload())
    assert created.status_code == 303
    work = Work.objects.get()
    assert work.workspace == workspace
    assert created.url == reverse("work-detail", kwargs={"work_id": work.id})
    detail_url = reverse("work-detail", kwargs={"work_id": work.id})
    assert client.post(detail_url, _work_payload(status="revising")).status_code == 303
    work.refresh_from_db()
    assert work.status == Work.Status.REVISING
    assert work in [
        result.work
        for result in search_works(
            actor=account, workspace_id=workspace.id, query_text="Literary fantasy"
        )
    ]
    assert work.title.encode() in client.post(list_url, {"query": "Lantern"}).content
    assert b"No Works matched" in client.post(list_url, {"query": "absent phrase"}).content


def test_all_work_types_and_statuses_render_with_structure_counts() -> None:
    account, workspace = _owner()
    types = list(Work.WorkType.values)
    statuses = list(Work.Status.values)
    works = [
        _work(
            workspace,
            title=f"Synthetic Work {index}",
            work_type=work_type,
            status=statuses[index % len(statuses)],
        )
        for index, work_type in enumerate(types)
    ]
    response = _client(account).get(reverse("work-list"))
    assert response.status_code == 200
    for work in works:
        assert work.title.encode() in response.content
        assert work.get_work_type_display().encode() in response.content
        assert work.get_status_display().encode() in response.content
    assert b"0 Volumes" in response.content
    assert b"0 Chapters" in response.content


def test_volume_arc_chapter_creation_editing_order_and_full_hierarchy() -> None:
    account, workspace = _owner()
    work = _work(workspace)
    character = Character.objects.create(workspace=workspace, name="Synthetic POV")
    client = _client(account)

    assert (
        client.post(
            reverse("volume-create", kwargs={"work_id": work.id}), _volume_payload()
        ).status_code
        == 303
    )
    volume = Volume.objects.get()
    assert volume.order == 1024
    assert (
        client.post(
            reverse("arc-create", kwargs={"work_id": work.id}), _arc_payload(volume)
        ).status_code
        == 303
    )
    arc = Arc.objects.get()
    assert arc.volume == volume
    assert arc.order == 1024
    assert (
        client.post(
            reverse("chapter-create", kwargs={"work_id": work.id}),
            _chapter_payload(volume, arc, character),
        ).status_code
        == 303
    )
    chapter = Chapter.objects.get()
    assert chapter.volume == volume
    assert chapter.arc == arc
    assert chapter.pov_character == character
    assert chapter.order == 1024

    volume_url = reverse("volume-edit", kwargs={"work_id": work.id, "volume_id": volume.id})
    assert (
        client.post(volume_url, _volume_payload(order=1024, title="Volume One Revised")).status_code
        == 303
    )
    arc_url = reverse("arc-edit", kwargs={"work_id": work.id, "arc_id": arc.id})
    assert (
        client.post(arc_url, _arc_payload(volume, order=1024, status="complete")).status_code == 303
    )
    chapter_url = reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
    assert (
        client.post(
            chapter_url,
            _chapter_payload(volume, arc, character, order=1024, status="revising"),
        ).status_code
        == 303
    )
    volume.refresh_from_db()
    arc.refresh_from_db()
    chapter.refresh_from_db()
    assert volume.title == "Volume One Revised"
    assert arc.status == Arc.Status.COMPLETE
    assert chapter.status == Chapter.Status.REVISING


def test_skipped_levels_support_work_scene_and_work_chapter_scene() -> None:
    account, workspace = _owner()
    short_story = _work(
        workspace,
        title="A Short Crossing",
        work_type=Work.WorkType.SHORT_STORY,
    )
    novella = _work(workspace, title="A Narrow Sea", work_type=Work.WorkType.NOVELLA)
    direct_scene = create_scene(
        actor=account, workspace_id=workspace.id, title="Direct Scene"
    ).scene
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=direct_scene.id,
        values={
            "work": short_story,
            "volume": None,
            "arc": None,
            "chapter": None,
            "structure_order": None,
        },
    )
    chapter = create_chapter(
        actor=account,
        workspace_id=workspace.id,
        work_id=novella.id,
        values={
            "volume": None,
            "arc": None,
            "title": "Chapter One",
            "label": "1",
            "order": None,
            "status": Chapter.Status.OUTLINING,
            "summary": "",
            "pov_character": None,
            "notes": "",
        },
    )
    chapter_scene = create_scene(
        actor=account, workspace_id=workspace.id, title="Chapter Scene"
    ).scene
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=chapter_scene.id,
        values={
            "work": novella,
            "volume": None,
            "arc": None,
            "chapter": chapter,
            "structure_order": None,
        },
    )
    direct_scene.refresh_from_db()
    chapter_scene.refresh_from_db()
    assert direct_scene.work == short_story
    assert direct_scene.chapter is None
    assert chapter_scene.chapter == chapter
    assert chapter_scene.volume is None
    assert chapter_scene.arc is None


def test_invalid_cross_work_and_cross_workspace_hierarchies_are_rejected() -> None:
    account, workspace = _owner()
    work = _work(workspace, title="First Work")
    other_work = _work(workspace, title="Second Work")
    volume = create_volume(
        actor=account,
        workspace_id=workspace.id,
        work_id=other_work.id,
        values={
            "title": "Wrong Volume",
            "order": None,
            "status": "active",
            "summary": "",
            "notes": "",
        },
    )
    with pytest.raises(StoryStructureConflict):
        create_arc(
            actor=account,
            workspace_id=workspace.id,
            work_id=work.id,
            values={
                "volume": volume,
                "title": "Invalid Arc",
                "order": None,
                "status": "active",
                "summary": "",
                "purpose": "",
                "notes": "",
            },
        )
    other_account, other_workspace = _owner("other-story-structure@example.invalid")
    outsider = Character.objects.create(workspace=other_workspace, name="Other POV")
    with pytest.raises(StoryStructureConflict):
        create_chapter(
            actor=account,
            workspace_id=workspace.id,
            work_id=work.id,
            values={
                "volume": None,
                "arc": None,
                "title": "Invalid Chapter",
                "label": "",
                "order": None,
                "status": "drafting",
                "summary": "",
                "pov_character": outsider,
                "notes": "",
            },
        )
    del other_account


def test_existing_unassigned_scene_can_be_assigned_reordered_and_reassigned() -> None:
    account, workspace = _owner()
    first_work = _work(workspace, title="First Work")
    second_work = _work(workspace, title="Second Work")
    first_chapter = Chapter.objects.create(
        workspace=workspace,
        work=first_work,
        title="First Chapter",
        order=1024,
        status=Chapter.Status.DRAFTING,
    )
    second_chapter = Chapter.objects.create(
        workspace=workspace,
        work=second_work,
        title="Second Chapter",
        order=1024,
        status=Chapter.Status.DRAFTING,
    )
    scene = create_scene(actor=account, workspace_id=workspace.id, title="Movable Scene").scene
    assert scene.work is None
    assert scene.structure_order is None
    client = _client(account)
    placement_url = reverse("scene-placement-update", kwargs={"scene_id": scene.id})
    assert (
        client.post(
            placement_url,
            {
                "work": first_work.id,
                "volume": "",
                "arc": "",
                "chapter": first_chapter.id,
                "structure_order": 2048,
            },
        ).status_code
        == 303
    )
    scene.refresh_from_db()
    first_version = scene.version
    assert scene.chapter == first_chapter
    assert scene.structure_order == 2048
    assert (
        client.post(
            placement_url,
            {
                "work": second_work.id,
                "volume": "",
                "arc": "",
                "chapter": second_chapter.id,
                "structure_order": "",
            },
        ).status_code
        == 303
    )
    scene.refresh_from_db()
    assert scene.work == second_work
    assert scene.chapter == second_chapter
    assert scene.structure_order == 1024
    assert scene.version == first_version + 1


def test_scene_editor_placement_is_scoped_and_archived_read_only() -> None:
    account, workspace = _owner()
    work = _work(workspace)
    _, other_workspace = _owner("placement-other@example.invalid")
    hidden_work = _work(other_workspace, title="Hidden Work")
    scene = create_scene(actor=account, workspace_id=workspace.id, title="Placed Scene").scene
    client = _client(account)
    editor = client.get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert b"Story Placement" in editor.content
    assert work.title.encode() in editor.content
    assert hidden_work.title.encode() not in editor.content
    Scene.objects.filter(id=scene.id).update(lifecycle=Scene.Lifecycle.ARCHIVED)
    archived = client.get(reverse("scene-editor", kwargs={"scene_id": scene.id}))
    assert b"Archived Scene placement is read-only" in archived.content
    assert (
        client.post(
            reverse("scene-placement-update", kwargs={"scene_id": scene.id}),
            {"work": work.id, "volume": "", "arc": "", "chapter": "", "structure_order": 1},
        ).status_code
        == 404
    )
    scene.refresh_from_db()
    assert scene.work is None


def test_chapter_lists_scenes_in_order_and_supports_attach_and_create() -> None:
    account, workspace = _owner()
    work = _work(workspace)
    chapter = Chapter.objects.create(
        workspace=workspace,
        work=work,
        title="Ordered Chapter",
        order=1024,
        status=Chapter.Status.DRAFTING,
    )
    first = create_scene(actor=account, workspace_id=workspace.id, title="First Scene").scene
    second = create_scene(actor=account, workspace_id=workspace.id, title="Second Scene").scene
    for scene, order in ((first, 1024), (second, 2048)):
        update_scene_placement(
            actor=account,
            workspace_id=workspace.id,
            scene_id=scene.id,
            values={
                "work": work,
                "volume": None,
                "arc": None,
                "chapter": chapter,
                "structure_order": order,
            },
        )
    unassigned = create_scene(
        actor=account, workspace_id=workspace.id, title="Existing Unassigned"
    ).scene
    client = _client(account)
    detail_url = reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
    detail = client.get(detail_url)
    content = detail.content.decode()
    element_ids = re.findall(r'\bid="([^"]+)"', content)
    label_targets = re.findall(r'<label[^>]+for="([^"]+)"', content)
    assert len(element_ids) == len(set(element_ids))
    assert set(label_targets).issubset(element_ids)
    assert content.index(first.title) < content.index(second.title)
    assert reverse("scene-editor", kwargs={"scene_id": first.id}) in content
    assert (
        client.post(
            reverse("chapter-scene-attach", kwargs={"work_id": work.id, "chapter_id": chapter.id}),
            {"existing-scene-scene": unassigned.id},
        ).status_code
        == 303
    )
    unassigned.refresh_from_db()
    assert unassigned.chapter == chapter
    created = client.post(
        reverse("chapter-scene-create", kwargs={"work_id": work.id, "chapter_id": chapter.id}),
        {"new-scene-title": "Created in Chapter"},
    )
    assert created.status_code == 303
    assert Scene.objects.get(title="Created in Chapter").chapter == chapter


def test_work_detail_counts_structure_recent_items_and_unassigned_scenes() -> None:
    account, workspace = _owner()
    work = _work(workspace)
    volume = Volume.objects.create(
        workspace=workspace, work=work, title="Volume", order=1024, status="active"
    )
    arc = Arc.objects.create(
        workspace=workspace,
        work=work,
        volume=volume,
        title="Arc",
        order=1024,
        status="active",
    )
    chapter = Chapter.objects.create(
        workspace=workspace,
        work=work,
        volume=volume,
        arc=arc,
        title="Chapter",
        order=1024,
        status="drafting",
    )
    placed = create_scene(actor=account, workspace_id=workspace.id, title="Placed").scene
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=placed.id,
        values={
            "work": work,
            "volume": volume,
            "arc": arc,
            "chapter": chapter,
            "structure_order": None,
        },
    )
    unassigned = create_scene(actor=account, workspace_id=workspace.id, title="Unassigned").scene
    response = _client(account).get(reverse("work-detail", kwargs={"work_id": work.id}))
    for value in ("Volumes", "Arcs", "Chapters", placed.title, unassigned.title):
        assert value.encode() in response.content
    assert b"Choose placement" in response.content


def test_combined_search_distinguishes_works_and_chapters() -> None:
    account, workspace = _owner()
    work = _work(workspace, title="Needle Work", premise="A cobalt needle premise")
    chapter = Chapter.objects.create(
        workspace=workspace,
        work=work,
        title="Needle Chapter",
        label="Act Needle",
        order=1024,
        status="outlining",
        summary="A cobalt needle goal",
    )
    assert [
        result.work
        for result in search_works(
            actor=account, workspace_id=workspace.id, query_text="cobalt needle"
        )
    ] == [work]
    assert [
        result.chapter
        for result in search_chapters(
            actor=account, workspace_id=workspace.id, query_text="cobalt needle"
        )
    ] == [chapter]
    response = _client(account).post(
        reverse("scene-search"), {"query": "cobalt needle", "include_archived": ""}
    )
    assert response.status_code == 200
    for heading in (b">Works<", b">Chapters<"):
        assert heading in response.content
    assert reverse("work-detail", kwargs={"work_id": work.id}).encode() in response.content
    assert (
        reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id}).encode()
        in response.content
    )


def test_dashboard_reports_active_work_and_recent_link() -> None:
    account, workspace = _owner()
    active = _work(workspace, title="Current Draft", status=Work.Status.DRAFTING)
    _work(workspace, title="Archived Work", status=Work.Status.ARCHIVED)
    response = _client(account).get(reverse("workspace-home"))
    assert response.status_code == 200
    assert b"Active Works" in response.content
    assert b"1" in response.content
    assert active.title.encode() in response.content
    assert reverse("work-detail", kwargs={"work_id": active.id}).encode() in response.content


def test_deletion_is_confirmed_protective_and_never_cascades_scenes() -> None:
    account, workspace = _owner()
    work = _work(workspace)
    empty_volume = Volume.objects.create(
        workspace=workspace, work=work, title="Empty Volume", order=1024, status="planned"
    )
    chapter = Chapter.objects.create(
        workspace=workspace,
        work=work,
        title="Protected Chapter",
        order=1024,
        status="drafting",
    )
    scene = create_scene(actor=account, workspace_id=workspace.id, title="Protected Scene").scene
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        values={
            "work": work,
            "volume": None,
            "arc": None,
            "chapter": chapter,
            "structure_order": None,
        },
    )
    client = _client(account)
    volume_delete = reverse(
        "volume-delete", kwargs={"work_id": work.id, "record_id": empty_volume.id}
    )
    assert client.get(volume_delete).status_code == 200
    assert client.post(volume_delete).status_code == 303
    assert not Volume.objects.filter(id=empty_volume.id).exists()
    work_delete = reverse("work-delete", kwargs={"work_id": work.id})
    blocked = client.post(work_delete)
    assert blocked.status_code == 409
    assert Work.objects.filter(id=work.id).exists()
    assert Chapter.objects.filter(id=chapter.id).exists()
    assert Scene.objects.filter(id=scene.id).exists()


def test_story_structure_is_workspace_scoped_and_mutations_are_post_only() -> None:
    account, workspace = _owner()
    work = _work(workspace, title="Visible Work")
    other_account, other_workspace = _owner("structure-scope-other@example.invalid")
    hidden = _work(other_workspace, title="Hidden Work")
    scene = create_scene(actor=account, workspace_id=workspace.id, title="Visible Scene").scene
    client = _client(account)
    listing = client.get(reverse("work-list"))
    assert work.title.encode() in listing.content
    assert hidden.title.encode() not in listing.content
    assert client.get(reverse("work-detail", kwargs={"work_id": hidden.id})).status_code == 404
    assert search_works(actor=account, workspace_id=workspace.id, query_text="Hidden") == []
    assert (
        client.get(reverse("scene-placement-update", kwargs={"scene_id": scene.id})).status_code
        == 405
    )
    assert (
        Client()
        .post(
            reverse("scene-placement-update", kwargs={"scene_id": scene.id}),
            {"work": work.id},
        )
        .status_code
        == 302
    )
    del other_account


def test_authenticated_qa_varied_work_shapes_and_long_content() -> None:
    account, workspace = _owner()
    long_token = "structure" * 80
    short = _work(
        workspace,
        title="Short Story",
        work_type=Work.WorkType.SHORT_STORY,
        status=Work.Status.COMPLETE,
        premise=long_token,
    )
    novella = _work(
        workspace,
        title="Novella",
        work_type=Work.WorkType.NOVELLA,
        status=Work.Status.HIATUS,
    )
    screenplay = _work(
        workspace,
        title="Screenplay",
        work_type=Work.WorkType.SCREENPLAY,
        status=Work.Status.PLANNING,
    )
    serial = _work(
        workspace,
        title="Web Serial",
        work_type=Work.WorkType.WEB_SERIAL,
        status=Work.Status.DRAFTING,
    )
    Chapter.objects.create(
        workspace=workspace,
        work=novella,
        title="Novella Chapter",
        order=1024,
        status="drafting",
    )
    Chapter.objects.create(
        workspace=workspace,
        work=screenplay,
        title="Opening Sequence",
        label="ACT I — SEQUENCE A",
        order=1024,
        status="outlining",
        summary=long_token,
    )
    volume = Volume.objects.create(
        workspace=workspace, work=serial, title="Serial Volume", order=1024, status="active"
    )
    arc = Arc.objects.create(
        workspace=workspace,
        work=serial,
        volume=volume,
        title="Serial Arc",
        order=1024,
        status="active",
    )
    Chapter.objects.create(
        workspace=workspace,
        work=serial,
        volume=volume,
        arc=arc,
        title="Serial Chapter",
        order=1024,
        status="drafting",
    )
    client = _client(account)
    for work in (short, novella, screenplay, serial):
        response = client.get(reverse("work-detail", kwargs={"work_id": work.id}))
        assert response.status_code == 200
        assert work.title.encode() in response.content
    assert (
        long_token.encode()
        in client.get(reverse("work-detail", kwargs={"work_id": short.id})).content
    )
