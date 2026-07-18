import os

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client, override_settings
from django.urls import reverse

from accounts.models import Account
from ai_assistance.adapters import AdapterResult, RetryableAdapterError
from ai_assistance.context import assemble_context, snapshot_is_stale
from ai_assistance.creative_services import run_creative_request
from ai_assistance.models import (
    AIChatMessage,
    AIChatSession,
    AIContextCharacterLink,
    AIContextPack,
    AIContextSceneLink,
)
from ai_assistance.tasks import get_task
from characters.models import Character
from scenes.services import create_scene, revise_scene_content
from stories.models import Chapter, Work
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]


def setup_domain(email="creative-ai@example.invalid"):
    account = Account.objects.create_user(email, password="Synthetic-Creative-Only!")
    workspace = Workspace.objects.create(name=f"Synthetic AI {email}")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    work = Work.objects.create(workspace=workspace, title="Synthetic Work", work_type="novel")
    chapter = Chapter.objects.create(
        workspace=workspace, work=work, title="Synthetic Chapter", order=1
    )
    scene = create_scene(actor=account, workspace_id=workspace.id, title="Synthetic Scene").scene
    scene.work = work
    scene.chapter = chapter
    scene.structure_order = 1
    scene.save(update_fields=("work", "chapter", "structure_order"))
    character = Character.objects.create(
        workspace=workspace,
        name="Synthetic Character",
        personality="Deliberately cautious",
        voice_notes="Short declarative sentences",
    )
    return account, workspace, client, work, chapter, scene, character


def test_context_pack_typed_links_deterministic_assembly_and_stale_snapshot():
    account, workspace, client, work, chapter, scene, character = setup_domain()
    pack = AIContextPack.objects.create(
        workspace=workspace,
        name="Synthetic Pack",
        work=work,
        chapter=chapter,
        author_instructions="Respect established facts",
        exclusions="No synthetic retcons",
    )
    AIContextCharacterLink.objects.create(
        pack=pack, character=character, priority=10, order=1, role="protagonist"
    )
    AIContextSceneLink.objects.create(
        pack=pack, scene=scene, priority=20, order=2, role="current prose"
    )
    with pytest.raises(IntegrityError):
        AIContextSceneLink.objects.create(pack=pack, scene=scene)
    other = Workspace.objects.create(name="Other AI scope")
    wrong = Character.objects.create(workspace=other, name="Wrong")
    with pytest.raises(ValidationError):
        AIContextCharacterLink(pack=pack, character=wrong).full_clean()
    first = assemble_context(
        pack, task=get_task("scene_brief"), instruction="Build a synthetic brief"
    )
    second = assemble_context(
        pack, task=get_task("scene_brief"), instruction="Build a synthetic brief"
    )
    assert first.text == second.text and first.context_hash == second.context_hash
    assert (
        "## Character" in first.text
        and "## Scene" in first.text
        and "revision identity" in first.text
    )
    assert "## Exclusions" in first.text and first.snapshot["sources"]
    assert not snapshot_is_stale(first.snapshot, workspace)
    revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="Synthetic changed prose",
    )
    assert snapshot_is_stale(first.snapshot, workspace)


@override_settings(
    AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True, AI_MODEL="", AI_OPENROUTER_API_KEY=""
)
def test_creative_request_review_conversion_chat_search_and_dashboard():
    account, workspace, client, work, chapter, scene, character = setup_domain(
        "workflow@example.invalid"
    )
    pack = AIContextPack.objects.create(
        workspace=workspace, name="Workflow Pack", work=work, chapter=chapter
    )
    AIContextCharacterLink.objects.create(pack=pack, character=character)
    request, suggestion = run_creative_request(
        account=account,
        workspace=workspace,
        task_key="monster_generate",
        instruction="Create a synthetic threshold creature",
        pack=pack,
    )
    assert request.state == "ready" and suggestion.state == "ready" and suggestion.structured_output
    review = client.get(reverse("ai-creative-review", args=(suggestion.id,)))
    assert review.status_code == 200 and b"Immutable Provider Output" in review.content
    client.post(
        reverse("ai-creative-review", args=(suggestion.id,)),
        {
            "reviewed_output": suggestion.reviewed_output,
            "review_notes": "Synthetic review",
            "action": "accept",
        },
    )
    suggestion.refresh_from_db()
    assert suggestion.state == "accepted"
    conversion = client.post(
        reverse("ai-creative-convert", args=(suggestion.id,)),
        {
            "target_type": "creature",
            "title": "Synthetic Threshold Beast",
            "content": "Synthetic reviewed creature",
        },
    )
    assert (
        conversion.status_code == 302
        and workspace.creatures.filter(name="Synthetic Threshold Beast").exists()
    )
    chat = AIChatSession.objects.create(
        workspace=workspace,
        title="Synthetic Story Chat",
        context_pack=pack,
        work=work,
        chapter=chapter,
    )
    response = client.post(
        reverse("ai-chat-detail", args=(chat.id,)), {"content": "What synthetic path follows?"}
    )
    assert (
        response.status_code == 302
        and AIChatMessage.objects.filter(
            session=chat, role="assistant", suggestion__isnull=False
        ).exists()
    )
    search = client.post(reverse("scene-search"), {"query": "Synthetic Story Chat"})
    assert b"Story Chats" in search.content
    assert b"AI Studio" in client.get(reverse("workspace-home")).content


def test_provider_disabled_workspace_history_post_mutations_and_isolation():
    account, workspace, client, work, chapter, scene, character = setup_domain(
        "disabled@example.invalid"
    )
    page = client.get(reverse("ai-workspace"))
    assert page.status_code == 200 and b"No provider connection is available" in page.content
    pack_response = client.post(
        reverse("ai-context-pack-create"),
        {"name": "Disabled Pack", "status": "draft", "detail_level": "concise"},
    )
    assert pack_response.status_code == 302
    pack = AIContextPack.objects.get(name="Disabled Pack")
    assert client.get(reverse("ai-context-pack-transition", args=(pack.id,))).status_code == 405
    client.post(reverse("ai-context-pack-transition", args=(pack.id,)), {"status": "archived"})
    pack.refresh_from_db()
    assert pack.status == "archived"
    other_account = Account.objects.create_user(
        "ai-outsider@example.invalid", password="Synthetic-Only!"
    )
    other_workspace = Workspace.objects.create(name="Other AI Workspace")
    WorkspaceGrant.objects.create(
        workspace=other_workspace, account=other_account, role="owner", state="active"
    )
    outsider = Client()
    outsider.force_login(other_account)
    assert outsider.get(reverse("ai-context-pack-detail", args=(pack.id,))).status_code == 404


@override_settings(
    AI_ENABLED=True,
    AI_ADAPTER="openrouter",
    DEBUG=False,
    AI_OPENROUTER_API_KEY="synthetic-secret",
    AI_MODEL="owner/fallback",
    AI_MODEL_WRITING="owner/writing",
    AI_MODEL_WRITING_ALTERNATE="owner/writing-alternate",
    AI_MODEL_OUTLINING="owner/outlining",
    AI_MODEL_BRAINSTORMING="owner/brainstorming",
    AI_MODEL_ANALYSIS="owner/analysis",
)
def test_creative_request_records_route_and_actual_alternate_model(monkeypatch):
    account, workspace, client, work, chapter, scene, character = setup_domain(
        "routing@example.invalid"
    )
    del client, work, chapter, scene, character
    attempts = []

    class Adapter:
        def __init__(self, model):
            self.model = model

        def generate(self, request):
            attempts.append(self.model)
            if self.model == "owner/writing":
                raise RetryableAdapterError("synthetic retry")
            return AdapterResult(
                "## Original\nSynthetic\n\n## Proposed Text\nSynthetic revised",
                "openrouter",
                self.model,
                "synthetic-operation",
                12,
                8,
            )

    monkeypatch.setattr(
        "ai_assistance.creative_services.creative_adapter", lambda model="": (Adapter(model), model)
    )
    request, suggestion = run_creative_request(
        account=account,
        workspace=workspace,
        task_key="scene_rewrite",
        instruction="Rewrite synthetic prose",
    )
    assert suggestion.state == "ready"
    assert attempts == ["owner/writing", "owner/writing-alternate"]
    assert request.routing_category == "writing"
    assert request.model_identifier == "owner/writing-alternate"
    assert request.provider_metadata["used_alternate"] is True
    assert request.provider_metadata["attempted_models"] == attempts
