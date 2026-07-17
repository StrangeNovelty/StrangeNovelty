import json
import os
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from accounts.models import Account
from decks.importing import import_package, load_and_validate_manifest
from decks.models import DeckCard, FavoriteCard, ImportBatch, JournalPrompt, ReviewStatus
from tests.test_decks_foundation import synthetic_package
from workspaces.models import Workspace, WorkspaceGrant

pytestmark = [
    pytest.mark.postgresql,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(
        not os.environ.get("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is required"
    ),
]
PASSWORD = "Synthetic-Deck-Only!"


def owner(email="deck@example.invalid"):
    account = Account.objects.create_user(email, password=PASSWORD)
    workspace = Workspace.objects.create(name="Synthetic Deck Workspace")
    WorkspaceGrant.objects.create(
        workspace=workspace, account=account, role="owner", state="active"
    )
    client = Client()
    client.force_login(account)
    return account, workspace, client


def package_file(tmp_path: Path, mutate=None) -> Path:
    data = synthetic_package()
    if mutate:
        mutate(data)
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(data))
    return path


def test_validate_only_has_no_writes_and_commit_is_idempotent(tmp_path: Path) -> None:
    _, workspace, _ = owner()
    path = package_file(tmp_path)
    call_command(
        "import_deck_package", manifest=path, workspace=str(workspace.id), validate_only=True
    )
    assert DeckCard.objects.count() == ImportBatch.objects.count() == 0
    call_command("import_deck_package", manifest=path, workspace=str(workspace.id), commit=True)
    assert DeckCard.objects.count() == 1 and ImportBatch.objects.count() == 1
    card = DeckCard.objects.get()
    assert card.review_status == ReviewStatus.PENDING
    assert card.extraction_confidence == "medium" and card.original_extracted_snapshot["prompt"]
    call_command("import_deck_package", manifest=path, workspace=str(workspace.id), commit=True)
    assert DeckCard.objects.count() == 1 and ImportBatch.objects.count() == 2


def test_status_mapping_all_confidence_levels_and_human_content_preservation(
    tmp_path: Path,
) -> None:
    _, workspace, _ = owner()

    def mutate(data):
        base = data["cards"][0]
        for suffix, confidence in (("-high", "high"), ("-low", "low")):
            card = dict(base)
            card["stable_source_id"] += suffix
            card["confidence"] = confidence
            data["cards"].append(card)
        data["manual_review"]["missing_text"] = [{"id": "synthetic-card-1-low"}]
        data["manual_review"]["visual_symbol_review"] = [{"id": "synthetic-card-1-high"}]

    path = package_file(tmp_path, mutate)
    package, _ = load_and_validate_manifest(path)
    assert package
    report = import_package(package=package, workspace=workspace, commit=True)
    assert (report.pending, report.needs_correction, report.needs_symbol_review) == (1, 1, 1)
    card = DeckCard.objects.get(stable_source_identity="synthetic-card-1")
    original = card.original_extracted_snapshot.copy()
    card.prompt = "Author correction"
    card.review_status = "approved"
    card.review_notes = "Reviewed"
    card.save()
    data = json.loads(path.read_text())
    data["cards"][0]["prompt"] = "Changed extraction"
    path.write_text(json.dumps(data))
    package, _ = load_and_validate_manifest(path)
    assert package
    import_package(package=package, workspace=workspace, commit=True)
    card.refresh_from_db()
    assert (
        card.prompt == "Author correction"
        and card.review_status == "approved"
        and card.original_extracted_snapshot == original
    )
    import_package(
        package=package, workspace=workspace, commit=True, refresh_original_snapshots=True
    )
    card.refresh_from_db()
    assert (
        card.prompt == "Author correction"
        and card.original_extracted_snapshot["prompt"] == "Changed extraction"
    )


def test_review_library_actions_scope_and_source_unavailable(tmp_path: Path) -> None:
    _, workspace, client = owner()
    path = package_file(tmp_path)
    package, _ = load_and_validate_manifest(path)
    assert package
    import_package(package=package, workspace=workspace, commit=True)
    card = DeckCard.objects.get()
    detail = client.get(reverse("deck-card-detail", args=(card.id,)))
    assert detail.status_code == 200
    assert client.get(reverse("deck-card-library")).content.count(b"Synthetic Threshold") == 0
    assert (
        b"Synthetic Threshold"
        in client.get(reverse("deck-card-library") + "?include_unapproved=1").content
    )
    review = client.get(reverse("deck-review-card", args=(card.id,)))
    assert review.status_code == 200 and b"Source render unavailable" in review.content
    assert str(tmp_path).encode() not in review.content
    assert client.get(reverse("deck-favorite-toggle", args=(card.id,))).status_code == 405
    client.post(reverse("deck-favorite-toggle", args=(card.id,)))
    assert FavoriteCard.objects.filter(workspace=workspace, card=card).exists()
    client.post(reverse("deck-active-toggle", args=(card.id,)))
    card.refresh_from_db()
    assert not card.is_active
    other_account, other_workspace, other_client = owner("other-deck@example.invalid")
    assert other_client.get(reverse("deck-card-detail", args=(card.id,))).status_code == 404


def test_approve_continue_filters_custom_card_guidance_and_journal(tmp_path: Path) -> None:
    _, workspace, client = owner()
    path = package_file(tmp_path)
    data = json.loads(path.read_text())
    second = dict(data["cards"][0])
    second["stable_source_id"] = "synthetic-card-2"
    second["title"] = "Synthetic Second"
    data["cards"].append(second)
    path.write_text(json.dumps(data))
    package, _ = load_and_validate_manifest(path)
    assert package
    import_package(package=package, workspace=workspace, commit=True)
    cards = list(DeckCard.objects.order_by("stable_source_identity"))
    save_url = reverse("deck-review-card", args=(cards[0].id,)) + "?status=pending"
    queue_next_id = client.get(save_url).context["next_id"]
    response = client.post(
        save_url,
        {
            "save_continue": "1",
            "next_id": queue_next_id,
            "title": "Corrected synthetic title",
            "prompt": cards[0].prompt,
            "instructions": cards[0].instructions,
            "examples": cards[0].examples,
            "back_content": "",
            "role": "",
            "suit": "",
            "mechanical_color": "",
            "modifiers": "[]",
            "symbols": "[]",
            "tags": "[]",
            "review_notes": "",
            "author_notes": "",
        },
    )
    cards[0].refresh_from_db()
    assert cards[0].title == "Corrected synthetic title"
    assert response.url == reverse("deck-review-card", args=(queue_next_id,)) + "?status=pending"
    url = reverse("deck-review-action", args=(cards[0].id,)) + "?status=pending"
    response = client.post(
        url,
        {
            "action": "approved_continue",
            "next_id": cards[1].id,
            "title": cards[0].title,
            "prompt": cards[0].prompt,
            "instructions": cards[0].instructions,
            "examples": cards[0].examples,
            "back_content": "",
            "role": "",
            "suit": "",
            "mechanical_color": "",
            "modifiers": "[]",
            "symbols": "[]",
            "tags": "[]",
            "review_notes": "",
            "author_notes": "",
        },
    )
    cards[0].refresh_from_db()
    assert cards[0].review_status == "approved" and response.url.endswith("?status=pending")
    assert client.get(reverse("deck-guidance")).status_code == 200
    assert (
        client.get(
            reverse("deck-spread-detail", args=(workspace.decks.get().spreads.get().id,))
        ).status_code
        == 200
    )
    journal = workspace.journal_templates.get()
    assert (
        client.get(reverse("deck-journal-detail", args=(journal.id,))).status_code == 200
        and JournalPrompt.objects.count() == 1
    )
    deck = workspace.decks.get()
    response = client.post(
        reverse("deck-custom-card-create"),
        {
            "deck": deck.id,
            "title": "Author-made synthetic",
            "prompt": "Custom prompt",
            "instructions": "",
            "examples": "",
            "role": "",
            "suit": "",
            "mechanical_color": "",
            "modifiers": "[]",
            "symbols": "[]",
            "tags": "[]",
            "author_notes": "",
            "is_active": "on",
        },
    )
    assert response.status_code == 302
    custom = DeckCard.objects.get(is_custom=True)
    assert custom.review_status == "approved"
    import_package(package=package, workspace=workspace, commit=True)
    assert DeckCard.objects.filter(id=custom.id).exists()


def test_import_transaction_rolls_back_on_database_failure(tmp_path: Path, monkeypatch) -> None:
    _, workspace, _ = owner()
    path = package_file(tmp_path)
    package, _ = load_and_validate_manifest(path)
    assert package

    def fail(*args, **kwargs):
        raise IntegrityError("synthetic rollback")

    monkeypatch.setattr(JournalPrompt.objects, "create", fail)
    with pytest.raises(IntegrityError):
        import_package(package=package, workspace=workspace, commit=True)
    assert DeckCard.objects.count() == 0 and ImportBatch.objects.count() == 0
