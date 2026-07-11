# Agent Instructions

These instructions apply to all coding agents working in the Strange Novelty repository.

## Read Before Working

Read the documents relevant to the task before making changes:

- For product intent, user experience, or feature behavior, read:
  - `docs/product/vision.md`
  - `docs/product/principles.md`
  - `docs/product/scope.md`
  - `docs/product/roadmap.md`
- For architecture or implementation work, read:
  - `docs/architecture/overview.md`
  - the relevant documents under `docs/architecture/`
  - `docs/decisions/README.md`
  - any applicable decision records
- For AI context, retrieval, or model integration work, also read:
  - `docs/architecture/ai-context.md`
- For data storage, entities, relationships, content states, or provenance, also read:
  - `docs/architecture/data-model.md`
- For authentication, authorization, privacy, secrets, logging, or threat-sensitive work, also read:
  - `docs/architecture/security.md`
- For external services or integrations, also read:
  - `docs/architecture/integrations.md`
- For work informed by the old Story Engine, also read:
  - `docs/reference/story-engine-audit.md`

If a referenced document is empty or incomplete, do not invent a durable decision silently. Identify the gap and ask for direction when it materially affects the task.

## Repository Safety

Inspect `git status` before making changes. Preserve unrelated work and do not overwrite or discard user changes.

Never modify anything under:

`/home/burmuss/projects/the-story-engine`

The old Story Engine is reference-only. Do not treat story content found there as current canon. Imported or referenced story material must remain distinguishable from author-approved canon.

Never commit:

- `private-data/`;
- secrets or secret-bearing configuration;
- manuscripts or unpublished story material;
- artwork or private visual assets;
- databases or database snapshots;
- exports or backups;
- credentials, tokens, keys, or certificates.

If sensitive material appears in the working tree, stop and report it without reproducing its contents.

## Scope and Context

Use the narrowest AI context that can safely complete the task. Do not ingest an entire story directory or unrelated private material. Select context deliberately and explain its scope when relevant.

Make the smallest coherent change that satisfies the request. Avoid unrelated refactors, speculative features, broad formatting changes, and premature application code.

Do not install packages, run migrations, perform destructive operations, push commits, deploy software, or access external networks without explicit user approval.

Destructive operations include deleting data, rewriting Git history, discarding uncommitted work, resetting state, replacing databases, and irreversible transformations.

## Documentation and Decisions

Update relevant documentation when a durable product, architecture, security, data, integration, or operational decision changes.

Record significant durable decisions in the appropriate decision documentation. Do not let implementation become the only source of truth for a decision.

Keep documentation consistent with the product vision and principles. Preserve authorial control, privacy, provenance, contextual canon, portability, backup, and recovery requirements.

## Verification and Handoff

Verify changes in proportion to their risk and scope.

At the end of the task, report:

- what changed;
- what was verified;
- any tests or checks that were not run;
- unresolved risks, assumptions, or documentation gaps.

Do not claim that work was verified unless the relevant check was actually performed.
