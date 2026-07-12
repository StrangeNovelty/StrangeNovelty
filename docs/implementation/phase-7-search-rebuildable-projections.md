# Phase 7 Implementation Record: Search and Rebuildable Projections

## Status

Completed on 2026-07-11.

This is an implementation record. ADR-0012, ADR-0010, and ADR-0015 remain authoritative.

## Scope

Phase 7 adds one rebuildable PostgreSQL full-text projection per current Scene, atomic invalidation and version-specific Job dispatch on Scene creation/content save, an allowlisted search-rebuild handler, stale-safe publication, authorized query service, bounded query-time excerpts, private POST UI, rebuild/reset commands, read-only admin, migrations, and tests.

No external search, semantic/vector search, embeddings, AI retrieval, recommendation, import, backup automation, MFA, Redis, broker, public API, frontend framework, or deployment feature was added.

## Projection Schema

`SceneSearchProjection` uses UUIDv4 identity and protected Workspace, one-to-one Scene, and source Revision references. It records source Scene version, projection schema version, search-configuration version, separate title/body `tsvector` fields, source content hash, and build timestamp. A composite GIN index supports matching.

There is exactly one current projection row per Scene. It contains no stored snippet, query history, arbitrary JSON, credentials, provider data, or revision-history copy. Vectors are derived private data and never authority.

## Configuration and Weighting

PostgreSQL configuration is explicit `simple`, versioned as `simple-v1`. Projection schema is `scene-search-v1`. `simple` avoids deployment-locale dependence and preserves creative/invented and mixed-language terms without English stemming.

Title vectors use weight A and body vectors weight B. Query rank sums title and body `SearchRank`, making title matches stronger under PostgreSQL's standard weight semantics. Exact tuning, phrases, prefix matching, stemming, dictionaries, and trigram assistance remain deferred.

## Atomic Invalidation and Dispatch

After Phase 3 commits a new current pointer/version inside its transaction, it deletes any old projection and enqueues a version-specific rebuild Job before the transaction exits. Scene creation and every accepted complete-content save therefore cannot commit while an older projection remains servable. A stale/conflicted save reaches neither invalidation nor enqueue.

Job dispatch failure rolls back the authoritative mutation because the Job is the accepted commit-coupled outbox. Later indexing failure does not roll back an already committed Scene; the Scene remains temporarily omitted until retry/rebuild.

The current application has no title or lifecycle mutation service. Direct model/admin mutation is unsupported. Any later reviewed title/lifecycle service must perform the same invalidation and dispatch; the handler and query service already enforce lifecycle at build/serve time.

## Search Job

The allowlisted type is `rebuild_scene_search_projection`. Job rows carry only Workspace, Scene target UUID, expected current Revision UUID, expected Scene version, and exact projection/configuration version. They contain no title or content.

Fingerprint inputs are Workspace, Scene, Revision, Scene version, projection schema, and configuration version. The scoped idempotency key includes Scene identity and version, so identical dispatch converges while a newer version creates distinct work.

## Handler and Publication

The handler reloads its Job, then locks the Workspace-scoped Scene and follows `Scene.current_revision`. Missing/obsolete work succeeds as a no-op. Trashed Scenes delete projections. Active and archived Scenes build title/body vectors from the authoritative title and current Revision content.

Publication rechecks Workspace, pointer, version, lifecycle, and projection version while holding the Scene lock. It update-or-creates the one-to-one row, then constructs vectors in PostgreSQL. A slower old worker cannot overwrite newer state; duplicate current-version workers converge.

Operational database unavailability maps to Phase 6 retryable failure. No raw content is logged or stored in Job evidence.

## Query Service

`search_scenes()` requires current authenticated Workspace authorization, a trimmed query of at most 200 characters, an archived flag, and limit 1–50. Blank queries return no results.

Queries always filter direct projection/Scene Workspace, exact current Revision pointer, exact Scene version, schema/configuration versions, and lifecycle. Active is default; archived requires explicit inclusion; trashed is always excluded. Known-stale or missing projections are omitted. Ordering is rank, Scene ordering, then stable Scene UUID.

Projection presence, rank, Job IDs, and UUID possession grant no authority. Revoked grants take effect on every search request.

## Snippets

Snippets are not stored. The service creates a plain-text excerpt at query time from the authorized source Revision, centered near the first case-insensitive query token and bounded to 240 characters plus ellipses. It emits no database markup; Django escapes it normally. Highlight markup and phrase fragments remain deferred.

## HTTP and Accessibility

`GET /search/` displays the empty private form; `POST /search/` performs search. Queries never enter URL/query strings. POST is CSRF protected, authenticated, Workspace-authorized, server-rendered, and private/no-store. The page includes labels, an archived checkbox, error summary, semantic no-result status, lifecycle labels, bounded snippets, and authorized editor links. It requires no JavaScript or external asset.

## Rebuild, Reset, and Restore

`enqueue_search_rebuild` requires explicit Workspace or all-Workspace scope, supports dry-run and limit 1–1000, prints counts only, and enqueues without synchronous execution.

`reset_search_projections` requires dry-run or confirmation, supports identical scope/limit and optional enqueue, and deletes only derived projections. It never deletes Scenes, Revisions, Mutation Operations, Security Events, save requests, Jobs, or idempotency history.

After restore, Phase 6 unfinished Jobs are quarantined first. Projections are treated as untrusted, explicitly reset, and new rebuild Jobs explicitly enqueued. Workers never resume automatically.

## Admin and Privacy

Projection admin is staff-viewable and read-only, with no add/change/delete. Its list shows only source version, projection/configuration versions, and build time—never vector dumps or manuscript text.

Search code logs no queries, titles, snippets, content, vectors, or parser errors containing input. Security Events are not created for ordinary searches/clicks. No external telemetry was added.

## Migrations

- `src/jobs/migrations/0002_remove_job_job_type_valid_and_more.py`
- `src/scenes/migrations/0003_scenesearchprojection.py`

They add only bounded search Job expectation fields/type constraints and the protected projection/vector/GIN schema. There is no data migration, stored snippet/query history, JSON, embedding/vector-database field, AI table, or sample content.

Migrations were not applied because no safe explicit `TEST_DATABASE_URL` was configured. SQLite was not used.

## Tests

Phase 7 adds 7 database-free cases and 9 PostgreSQL-only cases. The complete repository suite reports 82 passed and 87 PostgreSQL cases skipped without `TEST_DATABASE_URL`; tests never fall back to SQLite.

Coverage includes projection shape/GIN/versioning, registry, excerpts, POST template/migration boundaries, atomic enqueue/invalidation, current publication, stale workers, lifecycle and authorization, stale omission, validation, CSRF/cache/escaping, and bounded reset/rebuild commands.

## Verification

Commands: locked dependency sync; local/test/safe-production Django checks; migration drift; full pytest; Ruff lint/format; mypy; `git diff --check`; and privacy/scope scans. PostgreSQL migrations and search execution were not run without a safe test database.

## Known Limitations

- PostgreSQL search execution remains unverified locally until a safe test database is supplied.
- Recently changed Scenes may be omitted until their Job succeeds.
- No title/lifecycle mutation service exists yet; direct row edits are unsupported.
- Search uses plain terms without phrase, prefix, typo tolerance, stemming, trigram, or semantic behavior.
- Excerpts are plain bounded text without highlighting.
- No recurring reconciliation scanner or automatic rebuild schedule exists.

## Deferred Work

Phase 8 supplies verified backup/archive/restoration behavior. Legacy import, AI suggestions, and production operations follow later. External search remains eligible only after measured PostgreSQL limitations and must remain derived and rebuildable.

## ADR Alignment

This implementation follows ADR-0012 by keeping search PostgreSQL-native, private, versioned, current-pointer based, stale-detectable, omit-on-stale, lifecycle-aware, and fully rebuildable. It follows ADR-0010 by using commit-coupled durable Jobs and at-least-once idempotent handling, and ADR-0015 by keeping private queries out of URLs and browser correctness server-side.
