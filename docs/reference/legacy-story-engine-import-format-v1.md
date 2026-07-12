# Legacy Story Engine Scene Export Format Version 1

## Purpose

This non-normative format is the only legacy input accepted by Phase 9. It is a bounded UTF-8 JSON envelope intended to be produced later by a separately reviewed, read-only extractor. Strange Novelty does not open a legacy database, execute legacy code, or follow paths and URLs.

## Envelope

The top-level object has exactly three fields:

- `format`: the literal `story-engine-scene-export`;
- `schema_version`: the integer `1`; and
- `scenes`: an array of no more than 2,000 Scene records.

The complete file is limited to 25,000,000 bytes and 20,000 Revision records. It must be a regular, non-symlink UTF-8 file.

## Scene Record

Required fields are `id`, `title`, `current_revision_id`, and `revisions`. Optional supported fields are `lifecycle` and `ordering`. Other Scene fields are inventoried as unsupported findings; they do not become target data.

- `id`: bounded legacy string or integer identity, retained only as provenance;
- `title`: trimmed non-empty text of at most 200 characters;
- `lifecycle`: `active`, `archived`, or `trashed`, defaulting to `active`;
- `ordering`: optional non-negative integer;
- `current_revision_id`: explicit source Revision identity; and
- `revisions`: one or more complete Revision snapshots.

## Revision Record

Revision records allow exactly `id`, `sequence`, `content`, and optional `created_at`.

- `id`: bounded legacy source identity;
- `sequence`: positive source ordering evidence, not a target revision number;
- `content`: complete UTF-8 plain text, subject to the existing Scene content limit;
- `created_at`: optional timezone-aware ISO-8601 timestamp.

Duplicate Scene IDs, duplicate Revision IDs or sequences within a Scene, NUL characters, unknown Revision fields, missing current references, malformed timestamps, and unsupported lifecycle values reject the artifact.

## Transformation

The transformation identifier is `story-engine-scenes-v1`. Scenes and Revisions receive new UUIDv4 target identities. Revision sequence determines deterministic staging order; `current_revision_id` alone selects the target current pointer. Content uses the existing NFC and LF normalization service. Source-byte and normalized-target SHA-256 hashes remain distinct evidence.

Missing ordering is assigned deterministically in sparse steps of 1024. Collisions move forward by the same step and produce warnings. Matching titles or normalized content are warning evidence only and never merge or overwrite records.

## Unsupported and Prohibited Material

Attachments, relationships, external references, paths, URLs, auth records, settings, sessions, cookies, credentials, provider configuration, MFA/recovery material, deployment data, scripts, SQL, templates, macros, and executable serialization are unsupported. The parser does not retrieve, open, expand, import, or execute them.
