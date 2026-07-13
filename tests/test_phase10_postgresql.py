import os
import re

import pytest
from django.http import Http404
from django.test import Client, override_settings
from django.utils import timezone

from accounts.models import Account
from ai_assistance.adapters import (
    AdapterResult,
    AmbiguousAdapterError,
    RetryableAdapterError,
)
from ai_assistance.exceptions import AIRequestConflict, StaleSuggestion
from ai_assistance.models import AIRequest, AISuggestion, AISuggestionApplication, ProviderEffect
from ai_assistance.services import (
    apply_suggestion,
    cancel_ai_request,
    quarantine_unfinished_ai_requests,
    request_suggestion,
    suggestion_is_stale,
)
from jobs.models import Job
from jobs.services import claim_jobs, execute_claim
from scenes.models import MutationOperation, Scene, SceneRevision
from scenes.services import create_scene, revise_scene_content
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="requires PostgreSQL"),
]


def _domain() -> tuple[Account, Workspace, Scene]:
    account = Account.objects.create_user(
        "phase10@example.invalid", password="Synthetic-Test-Only!"
    )
    workspace = Workspace.objects.create(name="Synthetic Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace,
        account=account,
        role=WorkspaceGrant.Role.OWNER,
        state=WorkspaceGrant.State.ACTIVE,
    )
    scene = create_scene(actor=account, workspace_id=workspace.id, title="Synthetic Scene").scene
    return account, workspace, scene


def _assert_unique_labeled_ids(html: str) -> None:
    ids = re.findall(r'\bid="([^"]+)"', html)
    label_targets = re.findall(r'\bfor="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    assert set(label_targets) <= set(ids)


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_enqueue_is_authorized_idempotent_and_contains_no_private_text() -> None:
    account, _, scene = _domain()
    first = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="a" * 32,
    )
    second = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="a" * 32,
    )
    assert not first.replayed and second.replayed
    assert first.request.id == second.request.id
    job = Job.execution_objects.get(id=first.request.job_id)
    assert job.target_id == first.request.id
    assert not hasattr(job, "instruction") and not hasattr(job, "content")
    with pytest.raises(AIRequestConflict):
        request_suggestion(
            account=account,
            scene_id=scene.id,
            instruction="Changed synthetic instruction",
            idempotency_key="a" * 32,
        )


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_worker_creates_non_authoritative_suggestion_and_effect() -> None:
    account, _, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="b" * 32,
    ).request
    claimed = claim_jobs(worker_id="phase10-worker", batch_size=10)
    ai_claim = next(item for item in claimed if item.job.id == request.job_id)
    execute_claim(ai_claim)
    request.refresh_from_db()
    suggestion = AISuggestion.objects.get(request=request)
    assert request.state == AIRequest.State.COMPLETED
    assert suggestion.state == AISuggestion.State.READY
    assert suggestion.original_output == request.source_revision.content
    assert (
        ProviderEffect.objects.get(request=request).outcome == ProviderEffect.Outcome.KNOWN_SUCCESS
    )
    assert scene.current_revision_id == request.source_revision_id


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_stale_before_call_expires_without_suggestion(monkeypatch: pytest.MonkeyPatch) -> None:
    account, workspace, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="c" * 32,
    ).request
    revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="",
    )
    called = False

    def forbidden_adapter():
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr("ai_assistance.services.get_configured_adapter", forbidden_adapter)
    ai_claim = next(
        item
        for item in claim_jobs(worker_id="phase10-worker", batch_size=10)
        if item.job.id == request.job_id
    )
    execute_claim(ai_claim)
    request.refresh_from_db()
    assert request.state == AIRequest.State.EXPIRED
    assert not called and not AISuggestion.objects.filter(request=request).exists()


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_ambiguous_outcome_quarantines_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    account, _, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="d" * 32,
    ).request

    class Ambiguous:
        def generate(self, request):
            raise AmbiguousAdapterError("unknown")

    monkeypatch.setattr("ai_assistance.services.get_configured_adapter", lambda: Ambiguous())
    ai_claim = next(
        item
        for item in claim_jobs(worker_id="phase10-worker", batch_size=10)
        if item.job.id == request.job_id
    )
    job = execute_claim(ai_claim)
    request.refresh_from_db()
    assert job.state == Job.State.QUARANTINED
    assert request.state == AIRequest.State.QUARANTINED
    assert ProviderEffect.objects.get(request=request).outcome == ProviderEffect.Outcome.AMBIGUOUS


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_retryable_failure_uses_job_retry_and_then_converges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account, _, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="l" * 32,
    ).request
    calls = 0

    class RetryOnce:
        def generate(self, adapter_request):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RetryableAdapterError("temporary")
            return AdapterResult(
                proposed_text=adapter_request.source_content,
                provider="local_fake",
                model="deterministic-v1",
                operation_identifier="fake-retry",
                input_units=0,
                output_units=0,
            )

    monkeypatch.setattr("ai_assistance.services.get_configured_adapter", lambda: RetryOnce())
    first = next(
        item
        for item in claim_jobs(worker_id="phase10-worker", batch_size=10)
        if item.job.id == request.job_id
    )
    retry_job = execute_claim(first)
    assert retry_job.state == Job.State.RETRY_WAIT
    second = next(
        item
        for item in claim_jobs(
            worker_id="phase10-worker", batch_size=10, now=retry_job.available_at
        )
        if item.job.id == request.job_id
    )
    assert execute_claim(second).state == Job.State.SUCCEEDED
    assert AISuggestion.objects.filter(request=request).count() == 1


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_queued_cancellation_cancels_request_and_job() -> None:
    account, _, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="m" * 32,
    ).request
    cancelled = cancel_ai_request(account=account, request_id=request.id)
    assert cancelled.state == AIRequest.State.CANCELLED
    assert Job.execution_objects.get(id=request.job_id).state == Job.State.CANCELLED
    assert not AISuggestion.objects.filter(request=request).exists()


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_reviewed_partial_application_uses_ordinary_save_and_is_idempotent() -> None:
    account, _, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="e" * 32,
    ).request
    ai_claim = next(
        item
        for item in claim_jobs(worker_id="phase10-worker", batch_size=10)
        if item.job.id == request.job_id
    )
    execute_claim(ai_claim)
    suggestion = AISuggestion.objects.get(request=request)
    before_revisions = SceneRevision.objects.count()
    before_operations = MutationOperation.objects.count()
    applied = apply_suggestion(
        account=account, suggestion_id=suggestion.id, review_text="", idempotency_key="f" * 32
    )
    replay = apply_suggestion(
        account=account, suggestion_id=suggestion.id, review_text="", idempotency_key="f" * 32
    )
    assert applied.id == replay.id
    assert SceneRevision.objects.count() == before_revisions + 1
    assert MutationOperation.objects.count() == before_operations + 1
    assert (
        AISuggestionApplication.objects.get(suggestion=suggestion).revision_id
        == applied.resulting_revision_id
    )
    assert Job.execution_objects.filter(job_type="rebuild_scene_search_projection").count() >= 2


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_stale_suggestion_cannot_apply_and_revoked_grant_denies() -> None:
    account, workspace, scene = _domain()
    request = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="g" * 32,
    ).request
    ai_claim = next(
        item
        for item in claim_jobs(worker_id="phase10-worker", batch_size=10)
        if item.job.id == request.job_id
    )
    execute_claim(ai_claim)
    suggestion = AISuggestion.objects.get(request=request)
    revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="",
    )
    assert suggestion_is_stale(suggestion)
    with pytest.raises(StaleSuggestion):
        apply_suggestion(
            account=account, suggestion_id=suggestion.id, review_text="", idempotency_key="h" * 32
        )
    WorkspaceGrant.objects.filter(workspace=workspace, account=account).update(
        state="revoked", revoked_at=timezone.now()
    )
    with pytest.raises(Http404):
        apply_suggestion(
            account=account, suggestion_id=suggestion.id, review_text="", idempotency_key="i" * 32
        )


def test_restore_quarantines_unfinished_requests_only() -> None:
    account, workspace, scene = _domain()
    source = scene.current_revision
    assert source is not None
    common = {
        "workspace": workspace,
        "requested_by": account,
        "scene": scene,
        "source_revision": source,
        "source_scene_version": scene.version,
        "source_content_hash": source.content_sha256,
        "instruction": "Synthetic instruction",
        "instruction_hash": "a" * 64,
        "request_fingerprint": "b" * 64,
    }
    queued = AIRequest.objects.create(idempotency_key="j" * 32, **common)
    completed = AIRequest.objects.create(idempotency_key="k" * 32, state="completed", **common)
    assert quarantine_unfinished_ai_requests() == 1
    queued.refresh_from_db()
    completed.refresh_from_db()
    assert queued.state == AIRequest.State.QUARANTINED
    assert completed.state == AIRequest.State.COMPLETED


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_private_http_routes_are_csrf_protected_and_no_store() -> None:
    account, _, scene = _domain()
    client = Client(enforce_csrf_checks=True)
    client.force_login(account)
    response = client.get(f"/scenes/{scene.id}/ai/request/")
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    assert client.post(f"/scenes/{scene.id}/ai/request/", {}).status_code == 403


@override_settings(AI_ENABLED=True, AI_ADAPTER="local_fake", DEBUG=True)
def test_ai_workflow_pages_render_shell_navigation_and_review_controls() -> None:
    account, workspace, scene = _domain()
    client = Client()
    client.force_login(account)

    request_page = client.get(f"/scenes/{scene.id}/ai/request/")
    request_html = request_page.content.decode()
    assert request_page.status_code == 200
    assert request_html.count('<main id="main-content">') == 1
    assert 'class="app-shell"' in request_html
    assert 'aria-label="Primary navigation"' in request_html
    assert f'action="/scenes/{scene.id}/ai/request/"' not in request_html
    assert 'name="instruction"' in request_html
    assert 'name="idempotency_key"' in request_html
    assert "Only the selected current Scene Revision" in request_html
    assert f"Revision {scene.current_revision.revision_number}" in request_html
    assert f"Scene version {scene.version}" in request_html
    assert "Applying a suggestion does not make it Canon" in request_html
    _assert_unique_labeled_ids(request_html)

    requested = request_suggestion(
        account=account,
        scene_id=scene.id,
        instruction="Synthetic instruction",
        idempotency_key="n" * 32,
    ).request
    status_page = client.get(f"/ai/requests/{requested.id}/")
    status_html = status_page.content.decode()
    assert status_page.status_code == 200
    assert status_html.count('<main id="main-content">') == 1
    assert f'action="/ai/requests/{requested.id}/cancel/"' in status_html
    assert "Request completion never changes the Scene" in status_html
    _assert_unique_labeled_ids(status_html)

    ai_claim = next(
        item
        for item in claim_jobs(worker_id="phase10-shell-worker", batch_size=10)
        if item.job.id == requested.job_id
    )
    execute_claim(ai_claim)
    suggestion = AISuggestion.objects.get(request=requested)

    ready_page = client.get(f"/ai/requests/{requested.id}/")
    ready_html = ready_page.content.decode()
    assert ready_page.status_code == 200
    assert f'href="/ai/suggestions/{suggestion.id}/"' in ready_html
    assert f'action="/ai/requests/{requested.id}/cancel/"' not in ready_html

    review_page = client.get(f"/ai/suggestions/{suggestion.id}/")
    review_html = review_page.content.decode()
    review_text = " ".join(review_html.split())
    assert review_page.status_code == 200
    assert review_html.count('<main id="main-content">') == 1
    assert 'id="current-scene-text"' in review_html
    assert 'id="original-ai-output"' in review_html
    assert 'name="review_text"' in review_html
    assert f'action="/ai/suggestions/{suggestion.id}/apply/"' in review_html
    assert f'action="/ai/suggestions/{suggestion.id}/reject/"' in review_html
    assert f'action="/ai/suggestions/{suggestion.id}/expire/"' in review_html
    assert "does not make the text Canon" in review_html
    assert f"Source Revision {suggestion.source_revision.revision_number}" in review_text
    assert "Apply reviewed text" in review_html
    assert "disabled" not in review_html
    _assert_unique_labeled_ids(review_html)

    revise_scene_content(
        actor=account,
        workspace_id=workspace.id,
        scene_id=scene.id,
        expected_current_revision_id=scene.current_revision_id,
        expected_scene_version=scene.version,
        proposed_content="Changed after suggestion generation.",
    )
    stale_page = client.get(f"/ai/suggestions/{suggestion.id}/")
    stale_html = stale_page.content.decode()
    assert stale_page.status_code == 200
    assert 'class="ai-stale-warning" role="alert"' in stale_html
    assert "Direct application" in stale_html
    assert "is blocked" in stale_html
    assert "Apply reviewed text" in stale_html
    assert "disabled" in stale_html
    _assert_unique_labeled_ids(stale_html)
