import os

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from ai_assistance.models import (
    AIContextPack,
    AIContextSceneLink,
    AICreativeRequest,
    AICreativeSuggestion,
)
from scenes.services import create_scene, revise_scene_content
from stories.models import (
    Chapter,
    ChapterBeat,
    ChapterChecklistItem,
    ChapterPacingProfile,
    SceneBrief,
    Work,
    WritingDelta,
)
from stories.search import search_chapters
from stories.services import update_scene_placement
from stories.workshop import (
    capture_planning_snapshot,
    restore_planning_snapshot,
    writing_statistics,
)
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="PostgreSQL required"),
]


def setup_story():
    account = Account.objects.create_user(
        "advanced-chapter@example.invalid", "Synthetic-Only-Password!"
    )
    workspace = Workspace.objects.create(name="Synthetic Writing Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Serial", work_type="web_serial", status="drafting"
    )
    chapter = Chapter.objects.create(
        workspace=workspace, work=work, title="Synthetic Chapter", order=100
    )
    client = Client()
    client.force_login(account)
    return account, workspace, work, chapter, client


def placed_scene(account, chapter, content="one two"):
    result = create_scene(actor=account, workspace_id=chapter.workspace_id, title="Synthetic Scene")
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
            "volume": None,
            "arc": None,
            "chapter": chapter,
            "structure_order": 100,
        },
    )
    result.scene.refresh_from_db()
    return result


def test_beat_crud_scene_creation_and_scope_validation():
    account, workspace, work, chapter, client = setup_story()
    url = reverse("chapter-beat-create", kwargs={"work_id": work.id, "chapter_id": chapter.id})
    response = client.post(
        url,
        {
            "order": 1,
            "title": "A choice",
            "beat_type": "decision",
            "status": "planned",
            "summary": "Synthetic decision.",
        },
    )
    assert response.status_code == 303
    beat = chapter.structured_beats.get()
    response = client.post(
        reverse(
            "chapter-beat-scene-create",
            kwargs={"work_id": work.id, "chapter_id": chapter.id, "beat_id": beat.id},
        ),
        {"title": "Choice Scene"},
    )
    assert response.status_code == 303
    beat.refresh_from_db()
    assert beat.intended_scene.chapter == chapter
    other = Chapter.objects.create(workspace=workspace, work=work, title="Other", order=200)
    beat.intended_scene.chapter = other
    with pytest.raises(ValidationError):
        beat.full_clean()


def test_scene_brief_active_superseded_history_and_stale_revision():
    account, _, _, chapter, _ = setup_story()
    result = placed_scene(account, chapter)
    first = SceneBrief.objects.create(
        scene=result.scene,
        source_revision=result.revision,
        status="active",
        scene_function="Establish a synthetic choice.",
    )
    second = SceneBrief(scene=result.scene, source_revision=result.revision, status="active")
    with pytest.raises(ValidationError):
        second.full_clean(validate_constraints=True)
    first.status = "superseded"
    first.save()
    second.save()
    revised = revise_scene_content(
        actor=account,
        workspace_id=chapter.workspace_id,
        scene_id=result.scene.id,
        expected_current_revision_id=result.revision.id,
        expected_scene_version=result.scene.version,
        proposed_content="one two three four",
    )
    second.scene = revised.scene
    assert second.is_stale


def test_pacing_maps_snapshots_restore_checklist_and_search():
    account, workspace, work, chapter, client = setup_story()
    chapter.outline = "Original synthetic outline"
    chapter.save()
    beat = ChapterBeat.objects.create(
        chapter=chapter, order=1, title="Signal", summary="A searchable beacon"
    )
    profile = ChapterPacingProfile.objects.create(chapter=chapter, tension_score=7, humor_score=2)
    snapshot = capture_planning_snapshot(chapter, label="Before revision")
    chapter.outline = "Changed"
    chapter.save()
    beat.delete()
    profile.tension_score = 3
    profile.save()
    restore_planning_snapshot(snapshot)
    chapter.refresh_from_db()
    assert chapter.outline == "Original synthetic outline"
    assert chapter.structured_beats.get().title == "Signal"
    assert chapter.pacing_profile.tension_score == 7
    ChapterChecklistItem.objects.create(chapter=chapter, order=1, label="Continuity checked")
    assert client.get(reverse("series-map", kwargs={"work_id": work.id})).status_code == 200
    pacing = client.get(reverse("pacing-map", kwargs={"work_id": work.id}))
    assert pacing.status_code == 200 and b"Tension" in pacing.content
    assert (
        search_chapters(actor=account, workspace_id=workspace.id, query_text="searchable beacon")[
            0
        ].chapter
        == chapter
    )


def test_writing_deltas_are_positive_revision_keyed_and_dashboard_visible():
    account, workspace, _, chapter, client = setup_story()
    result = placed_scene(account, chapter, "one two three")
    assert WritingDelta.objects.get(revision=result.revision).word_delta == 3
    revised = revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=result.scene.id,
        expected_current_revision_id=result.revision.id,
        expected_scene_version=result.scene.version,
        proposed_content="one",
    )
    assert WritingDelta.objects.get(revision=revised.revision).word_delta == 0
    assert WritingDelta.objects.filter(revision=revised.revision).count() == 1
    stats = writing_statistics(workspace)
    assert stats["today"] == 3 and stats["week"] == 3 and stats["streak"] == 1
    response = client.get(reverse("workspace-home"))
    assert response.status_code == 200 and b"words added today" in response.content


def test_mutations_are_post_only_and_workspace_isolated():
    _, _, work, chapter, client = setup_story()
    beat = ChapterBeat.objects.create(chapter=chapter, order=1, title="Protected")
    delete_url = reverse(
        "chapter-beat-delete",
        kwargs={"work_id": work.id, "chapter_id": chapter.id, "beat_id": beat.id},
    )
    assert client.get(delete_url).status_code == 405
    other_account = Account.objects.create_user(
        "other-workshop@example.invalid", "Synthetic-Other-Password!"
    )
    other_client = Client()
    other_client.force_login(other_account)
    assert (
        other_client.get(
            reverse("chapter-detail", kwargs={"work_id": work.id, "chapter_id": chapter.id})
        ).status_code
        == 404
    )


def test_reviewed_ai_outline_and_scene_brief_require_explicit_application():
    account, workspace, work, chapter, client = setup_story()
    scene_result = placed_scene(account, chapter)
    pack = AIContextPack.objects.create(
        workspace=workspace, name="Synthetic Chapter Context", work=work, chapter=chapter
    )
    AIContextSceneLink.objects.create(pack=pack, scene=scene_result.scene)

    def suggestion(task_key, structured):
        request = AICreativeRequest.objects.create(
            workspace=workspace,
            requested_by=account,
            context_pack=pack,
            task_key=task_key,
            instruction="Synthetic reviewed request",
            state="ready",
            provider="local_fake",
            model_identifier="deterministic",
            context_snapshot={},
            assembled_context="Synthetic bounded context",
            context_hash="a" * 64,
        )
        return AICreativeSuggestion.objects.create(
            workspace=workspace,
            request=request,
            original_output="Synthetic immutable output",
            reviewed_output="Synthetic reviewed output",
            structured_output=structured,
            state="accepted",
        )

    outline = suggestion("chapter_outline", {"Key Beats": ["Opening signal", "Closing choice"]})
    assert chapter.structured_beats.count() == 0
    response = client.post(reverse("chapter-workshop-apply-suggestion", args=[outline.id]))
    assert response.status_code == 303
    assert list(chapter.structured_beats.values_list("title", flat=True)) == [
        "Opening signal",
        "Closing choice",
    ]
    assert chapter.planning_snapshots.filter(trigger="before_ai_application").exists()

    brief = suggestion(
        "scene_brief",
        {"Scene Function": "Test a synthetic choice", "Main Conflict": "Duty versus need"},
    )
    response = client.post(reverse("chapter-workshop-apply-suggestion", args=[brief.id]))
    assert response.status_code == 303
    active = scene_result.scene.briefs.get(status="active")
    assert active.source_revision_id == scene_result.scene.current_revision_id
    assert active.primary_conflict == "Duty versus need"
