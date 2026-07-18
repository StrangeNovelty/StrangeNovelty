import os

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import Account
from ai_assistance.models import (
    AIContextCharacterLink,
    AIContextDrawLink,
    BrainstormSession,
)
from characters.models import Character
from stories.models import Chapter, Work
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_domain(email="brainstorm@example.invalid"):
    account = Account.objects.create_user(email, password="Synthetic-Only!")
    workspace = Workspace.objects.create(name="Synthetic Story Engine")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    work = Work.objects.create(
        workspace=workspace, title="Synthetic Serial", work_type="web_serial"
    )
    chapter = Chapter.objects.create(
        workspace=workspace, work=work, title="Synthetic Opening", order=1
    )
    character = Character.objects.create(workspace=workspace, name="Synthetic Courier")
    return account, workspace, client, work, chapter, character


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True, AI_MODEL="")
def test_persistent_brainstorm_context_generation_and_apply_to_chapter():
    account, workspace, client, work, chapter, character = setup_domain()
    created = client.post(reverse("brainstorm-create"), {"mode": "plot"})
    assert created.status_code == 302
    session = BrainstormSession.objects.get(workspace=workspace)
    response = client.post(
        reverse("brainstorm-detail", args=(session.id,)),
        {
            "title": "Synthetic Directions",
            "mode": "plot",
            "work": work.id,
            "chapter": chapter.id,
            "characters": [character.id],
            "focus": "A bounded external problem",
            "exclusions": "No hidden betrayal",
            "author_notes": "The second direction has useful pressure.",
            "action": "generate",
        },
    )
    assert response.status_code == 302
    session.refresh_from_db()
    assert session.latest_suggestion_id
    assert AIContextCharacterLink.objects.filter(
        pack=session.context_pack, character=character
    ).exists()
    assert not AIContextDrawLink.objects.filter(pack=session.context_pack).exists()
    suggestion = session.latest_suggestion
    suggestion.state = "accepted"
    suggestion.save(update_fields=("state",))
    applied = client.post(
        reverse("ai-creative-convert", args=(suggestion.id,)),
        {
            "target_type": "chapter_outline",
            "action": "append",
            "title": "Synthetic directions",
            "content": "A reviewed synthetic outline direction.",
            "chapter": chapter.id,
        },
    )
    assert applied.status_code == 302
    chapter.refresh_from_db()
    assert "reviewed synthetic outline" in chapter.outline
    assert chapter.planning_snapshots.filter(trigger="before_ai_application").exists()


def test_brainstorm_workspace_isolation_and_post_only_creation():
    account, workspace, client, work, chapter, character = setup_domain("owner@example.invalid")
    del account, work, chapter, character
    assert client.get(reverse("brainstorm-create")).status_code == 405
    client.post(reverse("brainstorm-create"), {"mode": "realm"})
    session = workspace.brainstorm_sessions.get()
    other_account = Account.objects.create_user("other@example.invalid", password="Synthetic-Only!")
    other_workspace = Workspace.objects.create(name="Other Synthetic Story Engine")
    WorkspaceGrant.objects.create(
        workspace=other_workspace, account=other_account, role="owner", state="active"
    )
    outsider = Client()
    outsider.force_login(other_account)
    assert outsider.get(reverse("brainstorm-detail", args=(session.id,))).status_code == 404
