import os
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from characters.models import Character, CharacterGroup, CharacterScene, GroupMembership
from continuity.models import CharacterKnowledgeRecord, PlotThread, Secret
from scenes.models import Scene
from stories.models import Chapter, Work
from timeline.models import (
    EventChapterLink,
    EventCharacterLink,
    EventLocationLink,
    EventSceneLink,
    EventThreadLink,
    Timeline,
    TimelineEvent,
    TimelineEventRelation,
)
from timeline.services import (
    character_appearance_index,
    location_appearance_index,
    relation_warnings,
)
from workspaces.models import Workspace, WorkspaceGrant
from worldbuilding.models import (
    Creature,
    Location,
    SceneCreatureLink,
    SceneGroupLink,
    SceneItemLink,
    SceneLocationLink,
    WorldItem,
)

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_story(email="timeline@example.invalid"):
    account = Account.objects.create_user(email, password="Synthetic-Timeline-Only!")
    workspace = Workspace.objects.create(name=f"Synthetic Timeline {email}")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    work = Work.objects.create(workspace=workspace, title="Synthetic Chronicle", work_type="novel")
    chapter1 = Chapter.objects.create(workspace=workspace, work=work, title="Arrival", order=1)
    chapter2 = Chapter.objects.create(workspace=workspace, work=work, title="Revelation", order=2)
    scene1 = Scene.objects.create(
        workspace=workspace,
        work=work,
        chapter=chapter1,
        title="At the gate",
        ordering=1,
        structure_order=1,
    )
    scene2 = Scene.objects.create(
        workspace=workspace,
        work=work,
        chapter=chapter2,
        title="Below the tower",
        ordering=2,
        structure_order=1,
    )
    a = Character.objects.create(workspace=workspace, name="Synthetic A")
    b = Character.objects.create(workspace=workspace, name="Synthetic B")
    c = Character.objects.create(workspace=workspace, name="Synthetic C")
    chapter1.pov_character = a
    chapter1.save(update_fields=("pov_character",))
    CharacterScene.objects.create(workspace=workspace, character=a, scene=scene1)
    CharacterScene.objects.create(workspace=workspace, character=b, scene=scene1)
    CharacterScene.objects.create(workspace=workspace, character=a, scene=scene2)
    CharacterScene.objects.create(workspace=workspace, character=c, scene=scene2)
    location = Location.objects.create(
        workspace=workspace, name="Synthetic Gate", location_type="landmark"
    )
    SceneLocationLink.objects.create(
        workspace=workspace, scene=scene1, location=location, role="setting"
    )
    timeline = Timeline.objects.create(
        workspace=workspace, work=work, name="Primary Synthetic", status="active"
    )
    return (
        workspace,
        client,
        work,
        (chapter1, chapter2),
        (scene1, scene2),
        (a, b, c),
        location,
        timeline,
    )


def test_timeline_event_precisions_ordering_and_status_lifecycle():
    workspace, client, work, chapters, scenes, characters, location, timeline = setup_story()
    for index, precision in enumerate(("exact", "approximate", "relative", "unknown"), 1):
        TimelineEvent.objects.create(
            workspace=workspace,
            timeline=timeline,
            work=work,
            title=f"Synthetic {precision}",
            chronology_precision=precision,
            start_sort_value=None if precision == "unknown" else Decimal(index),
            display_date=precision,
        )
    ranged = TimelineEvent(
        workspace=workspace,
        timeline=timeline,
        work=work,
        title="Synthetic range",
        chronology_precision="range",
        start_sort_value=Decimal("10"),
        end_sort_value=Decimal("9"),
    )
    with pytest.raises(ValidationError):
        ranged.full_clean()
    response = client.post(
        reverse("timeline-event-create", args=(timeline.id,)),
        {
            "timeline": timeline.id,
            "work": work.id,
            "title": "Created through UI",
            "event_type": "story_event",
            "status": "planned",
            "significance": "major",
            "visibility": "author_only",
        },
    )
    assert response.status_code == 302
    event = TimelineEvent.objects.get(title="Created through UI")
    assert client.get(reverse("timeline-event-transition", args=(event.id,))).status_code == 405
    client.post(reverse("timeline-event-transition", args=(event.id,)), {"status": "established"})
    event.refresh_from_db()
    assert event.status == "established"
    client.post(reverse("timeline-transition", args=(timeline.id,)), {"status": "archived"})
    timeline.refresh_from_db()
    assert timeline.status == "archived"
    client.post(reverse("timeline-transition", args=(timeline.id,)), {"status": "active"})
    timeline.refresh_from_db()
    assert timeline.status == "active"


def test_connections_relations_reader_order_and_deterministic_warnings():
    workspace, client, work, chapters, scenes, characters, location, timeline = setup_story(
        "relations@example.invalid"
    )
    early = TimelineEvent.objects.create(
        workspace=workspace,
        timeline=timeline,
        work=work,
        title="Early",
        start_sort_value=Decimal("20"),
        display_date="Before dawn",
    )
    late = TimelineEvent.objects.create(
        workspace=workspace,
        timeline=timeline,
        work=work,
        title="Late",
        start_sort_value=Decimal("10"),
        display_date="After dawn",
    )
    EventChapterLink.objects.create(event=early, chapter=chapters[0], role="depicts")
    EventChapterLink.objects.create(event=late, chapter=chapters[1], role="reveals")
    EventSceneLink.objects.create(event=early, scene=scenes[0], role="depicts")
    EventCharacterLink.objects.create(event=early, character=characters[0], role="participant")
    EventLocationLink.objects.create(event=early, location=location, role="setting")
    relation = TimelineEventRelation(source=early, target=late, relation_type="before")
    relation.full_clean()
    relation.save()
    assert relation_warnings(early)
    with pytest.raises(ValidationError):
        TimelineEventRelation(source=early, target=early, relation_type="overlaps").full_clean()
    with pytest.raises(IntegrityError):
        TimelineEventRelation.objects.create(source=early, target=late, relation_type="before")
    other_workspace = Workspace.objects.create(name="Other timeline scope")
    wrong = Character.objects.create(workspace=other_workspace, name="Wrong scope")
    with pytest.raises(ValidationError):
        EventCharacterLink(event=early, character=wrong).full_clean()
    page = client.get(reverse("timeline-reader-order", args=(work.id,)))
    assert (
        page.status_code == 200
        and b"Chronology vs Reader Order" in page.content
        and b"reveals" in page.content
    )


def test_cross_reference_any_all_without_location_and_appearance_indexes():
    workspace, client, work, chapters, scenes, characters, location, timeline = setup_story(
        "xref@example.invalid"
    )
    a, b, c = characters
    any_page = client.post(
        reverse("timeline-cross-reference"),
        {"mode": "characters", "work": work.id, "characters": [a.id, b.id], "match": "any"},
    )
    assert (
        scenes[0].title.encode() in any_page.content
        and scenes[1].title.encode() in any_page.content
    )
    all_page = client.post(
        reverse("timeline-cross-reference"),
        {"mode": "characters", "characters": [a.id, b.id], "match": "all"},
    )
    assert (
        scenes[0].title.encode() in all_page.content
        and scenes[1].title.encode() not in all_page.content
    )
    without_page = client.post(
        reverse("timeline-cross-reference"),
        {"mode": "characters", "characters": [a.id], "without": b.id, "match": "any"},
    )
    assert (
        scenes[1].title.encode() in without_page.content
        and scenes[0].title.encode() not in without_page.content
    )
    place_page = client.post(
        reverse("timeline-cross-reference"),
        {"mode": "character_location", "characters": [a.id], "location": location.id},
    )
    assert (
        scenes[0].title.encode() in place_page.content
        and scenes[1].title.encode() not in place_page.content
    )
    assert character_appearance_index(a)["scene_count"] == 2
    assert location_appearance_index(location)["scene_count"] == 1
    group = CharacterGroup.objects.create(
        workspace=workspace, name="Synthetic Group", group_type="team"
    )
    GroupMembership.objects.create(workspace=workspace, group=group, character=a)
    SceneGroupLink.objects.create(workspace=workspace, scene=scenes[0], group=group)
    item = WorldItem.objects.create(workspace=workspace, name="Synthetic Key", item_type="key_item")
    SceneItemLink.objects.create(workspace=workspace, scene=scenes[0], item=item)
    creature = Creature.objects.create(
        workspace=workspace, name="Synthetic Beast", creature_type="monster"
    )
    SceneCreatureLink.objects.create(workspace=workspace, scene=scenes[0], creature=creature)
    for payload in (
        {"mode": "group_members", "group": group.id},
        {"mode": "item_character", "item": item.id, "characters": [a.id]},
        {"mode": "creature_location", "creature": creature.id, "location": location.id},
    ):
        assert (
            scenes[0].title.encode()
            in client.post(reverse("timeline-cross-reference"), payload).content
        )


def test_continuity_knowledge_panels_search_dashboard_and_isolation():
    workspace, client, work, chapters, scenes, characters, location, timeline = setup_story(
        "integration@example.invalid"
    )
    thread = PlotThread.objects.create(workspace=workspace, work=work, title="Synthetic Thread")
    secret = Secret.objects.create(
        workspace=workspace,
        work=work,
        thread=thread,
        title="Synthetic Secret",
        truth_statement="Synthetic truth",
    )
    CharacterKnowledgeRecord.objects.create(
        workspace=workspace,
        work=work,
        character=characters[0],
        secret=secret,
        knowledge_statement="Synthetic knowledge",
        learned_story_time="Bell one",
    )
    event = TimelineEvent.objects.create(
        workspace=workspace,
        timeline=timeline,
        work=work,
        title="Searchable chronology",
        short_summary="Synthetic temporal marker",
        start_sort_value=Decimal("2"),
    )
    EventThreadLink.objects.create(event=event, thread=thread, role="advances")
    EventChapterLink.objects.create(event=event, chapter=chapters[0], role="depicts")
    assert (
        b"Searchable chronology"
        in client.get(reverse("chapter-detail", args=(work.id, chapters[0].id))).content
    )
    search = client.post(reverse("scene-search"), {"query": "temporal marker"})
    assert b"Timeline Events" in search.content and b"Searchable chronology" in search.content
    assert b"Chronology" in client.get(reverse("workspace-home")).content
    other_account = Account.objects.create_user(
        "timeline-outsider@example.invalid", password="Synthetic-Only!"
    )
    other_workspace = Workspace.objects.create(name="Outsider workspace")
    WorkspaceGrant.objects.create(
        workspace=other_workspace, account=other_account, role="owner", state="active"
    )
    outsider = Client()
    outsider.force_login(other_account)
    assert outsider.get(reverse("timeline-event-detail", args=(event.id,))).status_code == 404
