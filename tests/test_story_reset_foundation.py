from pathlib import Path

from operations.story_reset import ResetAction, reset_action_for_model, story_reset_inventory_specs


def test_story_reset_classification_covers_every_project_model() -> None:
    specs = story_reset_inventory_specs()
    labels = {spec.label for spec in specs}
    assert "characters.Character" in labels
    assert "stories.Work" in labels
    assert "scenes.SceneRevision" in labels
    assert "decks.Deck" in labels
    assert "library.ResearchSource" in labels
    assert all(
        spec.workspace_lookup is not None
        for spec in specs
        if spec.action != ResetAction.PRESERVE
    )


def test_story_content_is_removed_but_operational_and_reference_data_is_not() -> None:
    specs = {spec.label: spec for spec in story_reset_inventory_specs()}
    for label in (
        "characters.Character",
        "characters.Ability",
        "stories.Work",
        "scenes.Scene",
        "scenes.SceneRevision",
        "continuity.PlotThread",
        "timeline.TimelineEvent",
        "worldbuilding.Location",
        "ai_assistance.AICreativeSuggestion",
        "publishing.ManuscriptProject",
        "legacy_imports.ImportBatch",
        "decks.SavedDraw",
        "library.LibraryConnection",
    ):
        assert specs[label].action == ResetAction.REMOVE
    for label in (
        "accounts.Account",
        "workspaces.Workspace",
        "workspaces.WorkspaceGrant",
        "security_events.SecurityEvent",
        "decks.Deck",
        "decks.DeckCard",
        "decks.FavoriteCard",
    ):
        assert specs[label].action == ResetAction.PRESERVE
    assert specs["library.ResearchSource"].action == ResetAction.REVIEW
    assert specs["library.ArtworkAsset"].action == ResetAction.REVIEW
    assert specs["jobs.Job"].action == ResetAction.REVIEW


def test_inspection_command_has_no_destructive_mode() -> None:
    root = Path(__file__).parents[1]
    command = (
        root / "src/operations/management/commands/inspect_story_reset.py"
    ).read_text()
    assert "--confirm" not in command
    assert ".delete(" not in command
    assert "No records were changed" in command


def test_each_model_classifier_returns_a_declared_action() -> None:
    for spec in story_reset_inventory_specs():
        assert reset_action_for_model(spec.model) in ResetAction
