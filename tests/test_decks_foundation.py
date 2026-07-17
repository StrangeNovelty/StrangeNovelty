import json
from pathlib import Path

from django.urls import reverse

from decks.importing import load_and_validate_manifest
from decks.models import DeckCard, DeckCardCue, FavoriteCard, ImportBatch, SpreadPosition


def synthetic_package() -> dict:
    return {
        "schema_version": 3,
        "source_collection": "synthetic-only",
        "inventory": [],
        "cards": [
            {
                "stable_source_id": "synthetic-card-1",
                "deck": "Synthetic Deck",
                "expansion": "Core",
                "category": "Prompt",
                "confidence": "medium",
                "title": "Synthetic Threshold",
                "prompt": "What changes at the threshold?",
                "instructions": "Choose one cue.",
                "examples": "A synthetic example.",
                "modifiers": ["quiet"],
                "symbols": ["synthetic-star"],
                "tags": ["test-only"],
                "primary_cues": ["arrival", "departure"],
                "source_file": "synthetic.pdf",
                "source_page": 1,
                "source_position": "row-1-col-1",
            }
        ],
        "rules": [
            {
                "deck": "Synthetic Deck",
                "expansion": "Core",
                "title": "Synthetic setup",
                "rule_type": "setup",
                "text": "Use synthetic records only.",
                "order": 1,
                "source_file": "synthetic.pdf",
                "source_page": 2,
                "confidence": "high",
            }
        ],
        "spreads": [
            {
                "deck": "Synthetic Deck",
                "expansion": "Core",
                "name": "Synthetic Pair",
                "purpose": "Test ordered positions.",
                "instructions": "Place two cards.",
                "minimum_cards": 2,
                "maximum_cards": 2,
                "allows_redraw": True,
                "positions": [
                    {"order": 1, "name": "First", "meaning": "Beginning"},
                    {"order": 2, "name": "Second", "meaning": "Change"},
                ],
                "source_file": "synthetic.pdf",
                "confidence": "high",
            }
        ],
        "journals": [
            {
                "title": "Synthetic Journal",
                "purpose": "Test journal hierarchy.",
                "instructions": "Answer in order.",
                "source_file": "synthetic.pdf",
                "sections": [
                    {
                        "order": 1,
                        "title": "Synthetic section",
                        "guidance": "Test guidance.",
                        "prompts": [
                            {
                                "order": 1,
                                "label": "Synthetic label",
                                "prompt": "Synthetic prompt?",
                                "response_type": "long_text",
                            }
                        ],
                    }
                ],
            }
        ],
        "manual_review": {
            "missing_text": [],
            "visual_symbol_review": [],
            "ambiguous_wording": [{"id": "synthetic-card-1"}],
        },
    }


def test_package_validation_accepts_synthetic_shape_without_database(tmp_path: Path) -> None:
    path = tmp_path / "synthetic-package.json"
    path.write_text(json.dumps(synthetic_package()))
    package, report = load_and_validate_manifest(path)
    assert package is not None
    assert report.accepted == 1
    assert report.pending == 1
    assert report.rules == report.spreads == report.journals == 1


def test_package_validation_rejects_malformed_duplicate_and_position_conflict(
    tmp_path: Path,
) -> None:
    malformed = synthetic_package()
    malformed["cards"].append(dict(malformed["cards"][0]))
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(malformed))
    package, report = load_and_validate_manifest(path)
    assert package is None
    assert report.duplicates == 1
    conflicting = synthetic_package()
    conflicting["spreads"][0]["positions"][1]["order"] = 1
    path.write_text(json.dumps(conflicting))
    package, report = load_and_validate_manifest(path)
    assert package is None and report.conflicts == 1


def test_deck_models_are_typed_workspace_owned_and_future_draw_models_are_absent() -> None:
    assert DeckCard._meta.pk.get_internal_type() == "UUIDField"
    assert DeckCardCue._meta.get_field("card").related_model is DeckCard
    assert SpreadPosition._meta.get_field("spread").related_model.__name__ == "SpreadTemplate"
    assert FavoriteCard._meta.get_field("workspace").related_model.__name__ == "Workspace"
    assert ImportBatch._meta.get_field("workspace").related_model.__name__ == "Workspace"
    import decks.models as models

    assert not hasattr(models, "SavedDraw")
    assert not hasattr(models, "DrawCard")


def test_deck_routes_and_templates_cover_private_review_contract() -> None:
    card = "00000000-0000-0000-0000-000000000001"
    assert reverse("deck-home") == "/decks/"
    assert reverse("deck-review-card", args=(card,)).startswith("/decks/review/")
    root = Path(__file__).parents[1]
    review = (root / "templates/decks/review_card.html").read_text()
    library = (root / "templates/decks/card_library.html").read_text()
    css = (root / "static/strange_novelty/app.css").read_text()
    assert "Original extracted snapshot" in review
    assert "Source render unavailable" in review
    assert "DECK_AUDIT_ROOT" not in review
    assert "Approve and Continue" in review and "csrf_token" in review
    assert "Approved by default" in library and "Include pending" in library
    assert ".review-grid" in css and "overflow-wrap: anywhere" in css


def test_repository_docs_and_fixtures_contain_no_commercial_card_content() -> None:
    root = Path(__file__).parents[1]
    ignored = (root / ".gitignore").read_text()
    package_doc = (root / "docs/reference/deck-import-package-v1.md").read_text()
    assert "/story engine deck/" in ignored
    assert "/*deck-import-package*.json" in ignored
    assert "Synthetic Threshold" not in package_doc
