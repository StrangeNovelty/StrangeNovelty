# Native Deck import package

`import_deck_package` accepts the private audit manifest schema version 3 directly. The command requires arrays named `cards`, `rules`, `spreads`, and `journals`; card records require unique `stable_source_id` and `deck` values. It validates duplicate card identities and spread-position ordering before any write.

The normalized internal package is versioned independently as native Deck package v1. It represents Decks, Expansions, Categories, Cards, ordered cues, Rules, Spreads and positions, Journals, source provenance, extraction confidence, and review flags. Commercial packages remain private and must match the repository ignore patterns.

Validate without writes:

```console
python manage.py import_deck_package --manifest /private/complete-manifest.json --workspace WORKSPACE_UUID --validate-only
```

Commit in one transaction by replacing `--validate-only` with `--commit`. Re-imports preserve current reviewed wording, review state, notes, custom cards, favorites, and author-created records. `--refresh-original-snapshots` deliberately refreshes only immutable comparison snapshots; it does not replace current reviewed wording.
