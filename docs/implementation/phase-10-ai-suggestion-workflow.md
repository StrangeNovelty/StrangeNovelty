# Phase 10 Implementation Record: AI Suggestion Workflow

## Status

Completed on 2026-07-11. ADR-0011 remains authoritative.

## Version 1 Capability

The only capability is `scene_revision_suggestion`. An authenticated owner explicitly selects one active Scene at its exact current Revision, supplies one bounded instruction, and receives one complete replacement proposal. The adapter gets no other Workspace content, retrieval, tools, files, browsing, or authority. Output is always a private non-authoritative Suggestion.

## AI Request and Context Manifest

`AIRequest` has UUIDv4 identity; protected Workspace, Account, Scene, source Revision, and Job references; exact Scene version/content hash; capability/template/configuration versions; private bounded instruction and instruction hash; provider/model classifications; request fingerprint and idempotency key; output limit; state/failure classifications; and lifecycle timestamps. It contains no assembled prompt, credentials, provider response, arbitrary JSON, or authority.

`AIContextManifest` separately fixes the exact Workspace, Scene, immutable source Revision, Scene version, content hash, capability, template/version, configuration, and `single-scene-v1` construction version. Context construction reads only that authorized Revision when the worker executes.

## Suggestion and Provider Evidence

`AISuggestion` has its own UUID and protected Request/Workspace/Scene/source references. It stores normalized original adapter output, separate human review text, output hash, state, bounded provider/model/template/receipt and usage classifications, review/disposition timestamps and actors, and the resulting Revision/version if applied. States are pending, ready, rejected, applied, expired, failed, and quarantined. Original output cannot be changed through ordinary instance updates.

`ProviderEffect` is separate per Job Attempt and records only provider classification, bounded operation identifier, intended/known-success/known-failure/ambiguous/cancelled outcome, ambiguity classification, and timestamps. It stores no instruction, context, output, prompt, URL, credential, or raw response. A receipt proves provider processing only, never authoritative mutation.

`AISuggestionApplication` is append-only protected provenance linking the Suggestion to the ordinary resulting Scene Revision and Mutation Operation, with applied-text hash and a human-edited flag.

## Provider Adapter and Configuration

The provider-neutral typed interface accepts capability, bounded instruction, exact source content, template/configuration identifiers, and output limit; it returns normalized proposal text, provider/model classifications, bounded receipt, and usage counts. Provider-specific objects never enter domain services.

`DeterministicFakeAdapter` is the only implementation. It returns the source text unchanged with deterministic bounded metadata, reads no files or environment secrets, and makes no network call. AI defaults to disabled. Local fake use requires explicit `AI_ENABLED=true`, `AI_ADAPTER=local_fake`, and debug/local settings. Production fails closed whenever AI is enabled because no reviewed real adapter exists. `.env.example` contains disabled values only.

## Enqueue, Fingerprint, and Job

The browser submits instruction and a bounded idempotency key in a CSRF-protected body. Django resolves current owner authority, locks the active Scene, captures its current Revision/version/hash, creates Request and Context Manifest, and commit-couples one `generate_ai_scene_suggestion` Job through Phase 6 generic idempotency. The semantic fingerprint covers Workspace, Account, Scene, source Revision/version/hash, instruction hash, capability, template, and configuration. Identical retries converge; changed meaning under the same key conflicts.

The Job carries only Workspace, Request UUID, source Revision UUID, expected Scene version, and configuration version. It is at-least-once, externally ambiguous work and contains no instruction, manuscript, prompt, response, receipt, credential, or key.

## Handler, Retry, and Ambiguity

Before calling the adapter, the handler revalidates the requesting Account's active owner Grant, Workspace/Scene lifecycle, exact current pointer/version/hash, Job configuration, and cancellation. A stale-before-call Request expires without adapter invocation. Effect intent is committed in a short transaction, adapter execution occurs without a long database transaction, and publication uses another short transaction.

Known retryable failures use Phase 6 bounded retry. Terminal failures stop. Ambiguous outcomes mark Request, Provider Effect, Job, and Attempt quarantined and never retry blindly. Cooperative cancellation cannot unsend a completed call. Duplicate completed delivery converges on the existing Suggestion. If the Scene changes during the call, the response may remain a ready but stale non-authoritative Suggestion; review/application detects and blocks it.

## Human Review and Application

Private server-rendered routes provide request, status, review, reject, expire, and apply operations. They require current owner authority, CSRF for mutations, no-store caching, safe escaping, keyboard-operable labeled forms, semantic status/alert messages, and no JavaScript correctness dependency. Instructions and output never enter URLs.

Review visibly separates current authoritative text, immutable original AI output, and editable complete review text. Editing the complete proposal represents human editing or partial acceptance; it is never a patch or automatic merge. Rejection and expiry are explicit POST dispositions and prevent application.

Application locks/revalidates the Suggestion and owner authority, compares exact source Revision/version/hash and lifecycle, and rejects stale work with HTTP 409. There is no force apply. A new Scene-save idempotency key passes the complete reviewed text through `save_scene_content`, producing exactly one ordinary immutable Scene Revision and Mutation Operation plus transactional search invalidation/rebuild dispatch. Suggestion state and application provenance commit in the same outer transaction. Applying does not create Canon.

## Recovery, Retention, and Privacy

Phase 8 restore now quarantines queued/running AI Requests alongside unfinished Jobs, clears no authoritative history, resets search, and starts nothing. Ready Suggestions remain non-authoritative and must pass current authorization/staleness checks. Applied Suggestions and protected application provenance remain historical. Portable Workspace archives continue to exclude AI Requests, Suggestions, instructions, provider effects, and provider credentials.

Exact retention periods and scheduled cleanup remain deferred. Unapplied private operational records may later be deleted under policy; protected application provenance prevents deletion from cascading into applied Scene Revisions or Mutation Operations. No custom encryption is introduced.

## Admin, Logging, and Security Events

AI Request, Context Manifest, Suggestion, Provider Effect, and application provenance administration is read-only. Broad lists show bounded state/capability/provider/model/time fields only; instructions, hashes, idempotency keys, outputs, review text, receipts, Workspace IDs, and target UUIDs are excluded.

No AI-specific successful event is added to Security Events. Jobs/Attempts, Requests, Effects, Suggestions, Mutation Operations, and Revisions retain their distinct meanings. Services and commands emit only bounded classifications/counts; no prompt, content, output, title, receipt, credential, or raw exception is logged.

## Migrations and Verification

Migrations add `ai_assistance.0001_initial` and extend the Job type/target/parameter allowlist. No data migration or sample private content is included. Migrations were not applied because `TEST_DATABASE_URL` was absent; SQLite was never used.

The complete suite reports 107 passed and 110 skipped. PostgreSQL AI integration cases skipped without the explicit safe test URL. Django local/test/safe-production checks, migration drift, Ruff, formatting, mypy, `git diff --check`, and privacy/scope scans passed. Locked dependency synchronization was attempted, but the `uv` executable was unavailable; the existing project environment supplied all verification tools.

## Known Limitations and Deferred Work

There is no real provider, SDK, streaming, callback, moderation API, provider reconciliation command, automatic retention, model pricing, production rate budget, or encrypted raw-response store. The fake adapter intentionally does not produce useful rewriting. Phase 11 addresses production operations without enabling AI until a separate reviewed provider/configuration decision exists.

## ADR Alignment

This implementation preserves ADR-0011's provider-neutral, exact-context, staged-output, human-approval, staleness, privacy, portability, and recovery boundaries; ADR-0010's durable Job/idempotency/lease/retry/cancellation/ambiguous-outcome semantics; and ADR-0015's private HTTP, complete-content save, dual concurrency, conflict, and progressive-enhancement rules.
