import os
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from scenes.services import create_scene
from stories.models import Chapter, Work
from stories.services import update_scene_placement
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="PostgreSQL required"),
]


def setup_workspace():
    account = Account.objects.create_user(
        f"integration-{uuid.uuid4()}@example.invalid", "Synthetic-Only-Password!"
    )
    workspace = Workspace.objects.create(name="Synthetic Integrated Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    return account, workspace, client


def place_scene(account, workspace, work, chapter, title, order):
    result = create_scene(actor=account, workspace_id=workspace.id, title=title)
    update_scene_placement(
        actor=account,
        workspace_id=workspace.id,
        scene_id=result.scene.id,
        values={
            "work": work,
            "volume": None,
            "arc": None,
            "chapter": chapter,
            "structure_order": order,
        },
    )
    return result.scene


def test_empty_workspace_onboarding_create_hub_and_help_are_authorized():
    _, _, client = setup_workspace()
    response = client.get(reverse("workspace-home"))
    assert response.status_code == 200
    assert b"Guided first use" in response.content
    assert b"Create a Work" in response.content
    assert b'aria-valuenow="0"' in response.content
    create = client.get(reverse("quick-create"))
    assert create.status_code == 200
    assert b"What are you making?" in create.content
    assert b"New Work" in create.content and b"New Story Chat" in create.content
    guide = client.get(reverse("product-guide"))
    assert guide.status_code == 200
    assert b"Track what the story promises" in guide.content
    assert b"Where does this go?" in guide.content
    assert b"Open guided first use" in guide.content
    assert Client().get(reverse("quick-create")).status_code == 302


def test_onboarding_detects_real_steps_and_can_be_reopened():
    _, workspace, client = setup_workspace()
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Guided Work", work_type="novel", status="planning"
    )
    Chapter.objects.create(workspace=workspace, work=work, title="Guided Chapter", order=10)

    dashboard = client.get(reverse("workspace-home"))
    assert dashboard.status_code == 200
    assert b'aria-valuenow="2"' in dashboard.content
    assert b"2 / 10" in dashboard.content

    hidden = client.get(reverse("workspace-home"), {"onboarding": "hide"})
    assert b"Guided first use" not in hidden.content
    reopened = client.get(reverse("workspace-home"), {"onboarding": "1"})
    assert b"Guided first use" in reopened.content


def test_work_command_center_and_scene_reader_order_navigation():
    account, workspace, client = setup_workspace()
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Journey", work_type="novel", status="drafting"
    )
    chapter = Chapter.objects.create(
        workspace=workspace, work=work, title="Synthetic Chapter", order=10
    )
    first = place_scene(account, workspace, work, chapter, "First Synthetic Scene", 10)
    second = place_scene(account, workspace, work, chapter, "Second Synthetic Scene", 20)
    third = place_scene(account, workspace, work, chapter, "Third Synthetic Scene", 30)

    work_page = client.get(reverse("work-detail", args=(work.id,)))
    assert work_page.status_code == 200
    for label in (b"Series Map", b"Story Memory", b"Creative Tools", b"Manuscripts"):
        assert label in work_page.content

    middle = client.get(reverse("scene-editor", args=(second.id,)))
    assert middle.status_code == 200
    assert reverse("scene-editor", args=(first.id,)).encode() in middle.content
    assert reverse("scene-editor", args=(third.id,)).encode() in middle.content
    assert reverse("chapter-detail", args=(work.id, chapter.id)).encode() in middle.content
    assert b"Save Scene" in middle.content


def test_integration_pages_do_not_leak_other_workspace_records():
    _, _, client = setup_workspace()
    _, other_workspace, _ = setup_workspace()
    Work.objects.create(
        workspace=other_workspace,
        title="Other Workspace Private Work",
        work_type="novel",
    )
    for route in ("workspace-home", "quick-create", "product-guide"):
        response = client.get(reverse(route))
        assert response.status_code == 200
        assert b"Other Workspace Private Work" not in response.content
