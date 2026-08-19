# Story Content Reset Runbook

## Current Boundary

The implemented reset workflow is read-only. It inventories one explicitly selected
Workspace and classifies records as `remove`, `review`, or `preserve`. It cannot delete,
update, archive, export, or back up any record.

This is intentionally the first gate. A destructive reset must not be implemented or run
until the author reviews the live inventory and explicitly approves the final treatment of
review-class records.

## Read-Only Inventory

Run against the intended environment and exact Workspace UUID:

```text
python manage.py inspect_story_reset --workspace '<workspace-uuid>'
```

Use `--format json` for a structured count report. The report contains model names and
counts only. It does not copy titles, character details, manuscript text, AI output, or
other creative content into a new artifact. Zero-count models are omitted from text output
unless `--include-zero` is supplied.

The command ends with `No records were changed` and has no confirmation or destructive
mode.

## Classification

`remove` currently includes story structures, Scenes and revisions, Characters and their
supporting records, continuity, timelines, worldbuilding, publishing, AI content, legacy
story-import staging, story-linked Deck Draw activity, and Library connections.

`review` includes Library sources, notes, artwork, collections, and operational Job records.
These may contain independent material worth keeping, story-specific material that should
be removed, or dependencies that require a deliberate choice.

`preserve` includes Accounts, authentication factors, Workspace ownership, Security Event
metadata, and the Deck reference catalog and favorites.

Every new project model must be classified before the inventory can run. Any non-preserved
model without a safe Workspace scope stops the command.

## Approval Gate Before Destructive Work

Before a destructive phase is designed or authorized, verify:

1. the environment and Workspace UUID;
2. live counts for all three classifications;
3. the exact treatment of every nonzero `review` model;
4. whether existing provider backup generations may expire normally or require a separate
   retention decision;
5. that no permanent archive of the incorrect story content will be created unless the
   author expressly requests one;
6. that Account, MFA, Workspace ownership, and Deck reference records remain outside the
   deletion scope; and
7. that the author provides a second explicit authorization after reviewing the report.

Immutable revision, mutation-operation, job, and audit boundaries make ad hoc shell deletes,
manual SQL, and per-record UI deletion unacceptable substitutes for this process.

## Verification Expectations for a Later Reset

A later approved reset must use maintenance mode, an atomic dependency-aware operation,
bounded non-content audit evidence, private-object reconciliation, search cleanup, job
quarantine, and post-operation count checks. It must prove that preserved records remain
usable and that story and AI records are absent before the site is reopened for clean data
entry.
