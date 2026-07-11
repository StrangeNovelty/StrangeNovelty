# ADR-0012: Search, Derived Projections, and Rebuildability

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 boundaries for PostgreSQL full-text search, current-record derived projections, freshness and stale-index handling, commit-coupled indexing Jobs, Workspace authorization, lifecycle eligibility, ranking, snippets, search normalization and versioning, rebuild and reindex, restoration, migration, retention, cleanup, and privacy, while exact Python, Django, PostgreSQL, projection tables and fields, search-vector representation, indexes, language configuration, dictionaries, tokenization, stemming, stop words, ranking weights, query syntax, trigram use and thresholds, snippet limits and rendering, polling and claim behavior, indexing concurrency, rebuild batches and schedules, freshness targets, telemetry buckets, retention periods, database roles, and deployment configuration remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; Django, PostgreSQL search, authorization, privacy, data modeling, jobs, backup/restoration, and migration perspectives

## Context

Version 1 requires private search and navigation across supported creative records. Search must feel useful and reasonably fresh without allowing an index, snippet, rank, or search-engine record to become authoritative or expose inaccessible manuscript content.

The accepted architecture establishes an immutable source and a clear current selector: Scene Revision alone stores authoritative normalized UTF-8 body text; Scene points to its current Revision and carries the integer version. Stable UUIDs identify both. Search must index that explicit current state rather than infer it from time, UUID order, or revision number.

ADR-0001 through ADR-0011 also require Django policy enforcement, PostgreSQL authority, Workspace scope, rebuildable derived data, bounded background Jobs, commit-coupled dispatch, at-least-once/idempotent processing, restore-time quarantine, private logs, and no semantic/vector/AI retrieval without a separate decision.

The old Story Engine's global search preserved useful ideas—fast search, snippets, record-type labels, and direct navigation—but used ad hoc `LIKE` queries across many tables, lacked Workspace/state/provenance filtering and freshness semantics, and ran in a broad client-side database trust model. Strange Novelty should preserve the workflow value, not those boundaries.

The decision must distinguish:

- authoritative Scene content from a search document;
- current Revision pointer from indexed Revision;
- search projection from archive/export;
- search result from authorization;
- rank from relevance certainty or truth;
- snippet from authoritative content;
- content normalization from search tokenization;
- query logging from security events;
- full-text search from semantic/vector search;
- indexing Job from domain mutation;
- indexing retry from user save retry;
- projection version from schema migration version;
- stale projection from stale author edit;
- missing projection from missing Scene;
- rebuild from restoration;
- reindex from migration;
- projection cleanup from domain deletion;
- archived Scene from trashed Scene;
- lifecycle eligibility from authorization;
- synchronous invalidation from asynchronous rebuild;
- database backup of projections from structured archive portability; and
- search-engine mechanism from search semantics.

Exact Python, Django, PostgreSQL, language configuration, dictionaries, stemming, stop words, trigram behavior, ranking weights, indexes, polling cadence, rebuild schedule, retention, projection size, and deployment remain undecided.

## Decision

If accepted, Version 1 will use the following architecture.

1. Use PostgreSQL-native full-text search inside the Django modular monolith before introducing an external search service.
2. Do not select Elasticsearch, OpenSearch, Solr, Meilisearch, Typesense, Algolia, a vector database, hosted search, semantic search, embeddings, recommendations, or autonomous retrieval for Version 1.
3. Maintain one rebuildable current-search projection per searchable Scene. The projection references Workspace, Scene, exact current Revision, Scene version, projection schema/search-normalization version, lifecycle/search eligibility, derived searchable fields, and build time.
4. Scene and current Revision remain authoritative. Projection ID, indexed text, rank, snippet, and index presence grant no authority and cannot replace source content.
5. Use hybrid indexing: the authoritative transaction synchronously records/increments source state and commit-couples an indexing Job; asynchronous workers build/publish the projection. A minimal current source marker/version makes stale projections detectable immediately.
6. Failed indexing never rolls back or falsifies a successful Scene save. Search may temporarily omit a changed Scene until a current projection exists.
7. A projection is valid for serving only when its Workspace, Scene, source Revision ID, and source Scene version equal authoritative current state and its projection version is the active serving version.
8. Known-stale projections are not returned as current results. Version 1 prefers omission with bounded freshness/status indication over showing stale private excerpts. Missing projection means indexing incomplete, not missing Scene.
9. Workers use ADR-0010 Job/Attempt/Idempotency/lease/retry/cancellation semantics. Writes are idempotent by source identity/version and use conditional publish so stale workers cannot replace newer projections.
10. Every query is authenticated, Workspace-scoped, lifecycle-filtered, and authorization-checked by Django before results/snippets are returned. Index presence and counts cannot confirm inaccessible records.
11. Ordinary search excludes trashed Scenes. Archived Scenes are excluded from default active search but may be included through an explicit authorized filter. Exact future record-type eligibility is documented per type.
12. Searchable Scene fields initially include bounded title and authoritative current body content. Later accepted metadata—hierarchy, tags, states, provenance categories, Characters, Locations, and Links—may add versioned bounded fields without changing authority.
13. Search-specific tokenization, dictionaries, stemming, weighting, ranking, and optional trigram assistance are derived/versioned behavior. They never mutate authoritative content or define identity.
14. Generate snippets/excerpts at query time from the authorized current projection or current authoritative source under version checks. Do not store long-lived snippets as standalone manuscript records.
15. Snippets are private, escaped/untrusted display text. Search result links resolve the authoritative Scene/current Revision through ordinary authorization.
16. Search rank is a relative heuristic for one query/configuration, not certainty, Canon, chronology, authority, or durable metadata.
17. Full rebuild must be possible from PostgreSQL authoritative records alone. Projection/index schema or tokenizer changes use versioned reindexing with controlled dual-version build and explicit serving cutover.
18. Database backups may contain projections for recovery speed, but structured portable archives omit them when rebuildable. Restoration treats projections as untrusted and normally discards/rebuilds them.
19. Restored unfinished indexing Jobs are quarantined or regenerated, never resumed blindly. Rebuild Jobs are safe to regenerate from authoritative state.
20. Projection cleanup cannot cascade to Scene, Revision, Link, provenance, archive, or backup records. Old versions have bounded cleanup after successful cutover/rollback evidence.
21. Raw search queries, result clicks, snippets, titles, and manuscript text are not broadly logged by default. Telemetry uses bounded latency/count/error/configuration/correlation data.
22. External search may be considered later only after measured PostgreSQL limits or deployment needs. Any external index remains derived, Workspace-scoped, authorization-filtered, and fully rebuildable.

## Terminology and Boundaries

An **authoritative source** is a domain record whose meaning persists independently of search. For Scene body search, it is Scene plus its explicit current Scene Revision.

A **search projection** is a derived current-record representation optimized for matching/ranking. A PostgreSQL search vector/index is a physical/search mechanism over that projection, not a second manuscript.

An **indexed Revision** is the Revision a projection was built from. The **current Revision** is the Scene pointer now. A mismatch means stale projection.

A **snippet/excerpt** is a query-specific private display fragment. It is not authoritative content, a separate revision, provenance, or export record.

**Content normalization** produces stored authoritative text under ADR-0006. **Search normalization/tokenization** derives searchable lexemes/configuration and may vary by language/version without rewriting content.

A **rebuild** recreates projections from authoritative records after loss/restore/corruption. A **reindex** changes projection/search configuration/version, usually through dual-version generation and cutover. Neither is restoration of domain data.

**Index lag** is the interval between authoritative commit and valid projection publication. A **missing projection** is derived-state absence, not proof that the source is absent. **Stale index** is a projection known not to match current source state.

Backlinks are reverse views of authoritative Links. If materialized, they follow the same rebuildable/source-version/freshness rules; Links remain authoritative.

## Search Architecture Principles

- Keep search in PostgreSQL/Django for Version 1.
- Index explicit current authoritative state only.
- Make every projection source-identifiable, versioned, stale-detectable, and rebuildable.
- Couple index intent to authoritative commit without extending the save transaction through heavy indexing.
- Prefer temporary omission over knowingly stale current-content display.
- Reauthorize every query/result/snippet.
- Never treat rank, index presence, or snippet as authority.
- Keep lifecycle eligibility explicit and distinct from authorization.
- Minimize derived private text and telemetry retention.
- Use ADR-0010 Jobs for async build/rebuild and restore reconciliation.
- Make duplicate attempts converge and stale workers unable to overwrite newer state.
- Allow loss of all projection data without loss of domain meaning.
- Keep semantic/vector/AI retrieval out of scope.
- Permit future external search only behind the same semantics.

## Authoritative Source Boundary

For a Scene projection, the authoritative inputs are:

- Scene UUID and Workspace UUID;
- explicit Scene current-Revision UUID;
- Scene integer version;
- current Revision exact normalized content and representation versions;
- current Scene title and later approved searchable metadata;
- lifecycle state and relevant eligibility fields; and
- later authoritative Link/parent/state records explicitly included by projection version.

The indexer loads these through Workspace-scoped Django query services. It never chooses maximum revision number, newest timestamp, highest UUID, latest insertion, or search-document state as current.

The projection does not become a write path back to Scene. Search-derived summaries/counts/excerpts cannot update title, content, lifecycle, order, provenance, links, or current pointer.

If source reads are inconsistent or change during build, the final conditional publish compares source Revision/version again. A stale build is discarded/retried against current state rather than published.

When Character, Location, and other Version 1 tables are physically introduced, each receives an explicit authoritative-source/projection contract; this ADR does not invent those schemas now.

## Search Projection Record

One current-Scene search projection contains logically:

- stable projection UUID or deterministic internal identity distinct from Scene identity;
- direct Workspace UUID;
- source Scene UUID;
- source current-Revision UUID;
- source Scene integer version;
- projection schema/version;
- search normalization/configuration version;
- derived title field;
- derived current body/search document or supported search-vector representation;
- bounded later metadata fields/type/lifecycle eligibility;
- build timestamp;
- build Job/Attempt/reference metadata where useful;
- freshness/publication status; and
- no credentials, sessions, secrets, prompts, provider responses, operational errors, or unrelated private records.

Only one projection version is active for serving per searchable source/configuration, although old/new versions may coexist during rebuild.

The record stores enough derived text or searchable representation to support PostgreSQL matching/highlighting. It is private duplicated content and receives equivalent authorization/storage/backup/logging protections.

Counts and summaries may live in the same projection or separate derived tables if later evidence warrants them. They always identify source version and algorithm version.

Backlink projections identify authoritative Link source/version/endpoints and can be independently rebuilt; they do not replace Link rows.

## Projection Freshness and Validity

A Scene projection is valid only when all are true:

- projection Workspace equals Scene Workspace;
- projection source Scene exists and is searchable under lifecycle policy;
- projection source Revision equals Scene current pointer;
- projection source Scene version equals current Scene version;
- projection schema/search-normalization version equals the active serving version; and
- projection is marked successfully published, not building/failed/retired.

The authoritative save/lifecycle/title/order transaction updates Scene version and creates the commit-coupled indexing Job. This immediately makes any old projection invalid by version mismatch even before the worker runs.

Search query joins/filters against authoritative Scene state or uses equivalent validated current markers so known-stale rows cannot be served accidentally. A projection status cache may optimize this but cannot be sole truth.

Freshness is observable through bounded counts/lag/oldest-pending metrics and authorized UI status. Metrics never contain titles, queries, snippets, or manuscript text.

If an unrelated metadata mutation is later proven not to affect search or eligibility, it may avoid rebuild through an explicit projection dependency rule; the current conservative policy follows Scene version until evidence supports finer-grained source versions.

## Indexing and Dispatch

Version 1 uses hybrid invalidation plus asynchronous rebuild.

1. The domain transaction changes authoritative Scene state and advances version under accepted rules.
2. The same transaction creates/updates a bounded commit-coupled indexing Job keyed by Workspace, Scene, source Revision/version, and projection version.
3. Commit makes both authoritative change and indexing intent durable.
4. Worker claims under ADR-0010, reauthorizes Workspace/source/lifecycle, and loads exact current inputs.
5. Worker computes derived document/vector outside long locks/transactions.
6. A short transaction conditionally publishes only if Scene current Revision/version and active target projection version still match.
7. Duplicate Jobs/Attempts converge on the same current projection; stale results are discarded.

For very small/title-only changes, synchronous projection calculation might appear simple, but blocking saves on text-search generation/index maintenance couples authoring latency/failure to derived work. It is rejected as the default.

A minimal synchronous invalidation/source-version update is part of the authoritative mutation; heavy derivation remains async. Failed indexing does not roll back committed content.

Full rebuild creates bounded per-Workspace/per-batch Jobs without one giant payload. Exact batching, concurrency, priority, polling, retry, and scheduling remain later decisions.

## Search Query Execution

The browser submits an authorized query through Django. Query text must not appear in URL paths/query strings where avoidable; state-changing protections are separate, but privacy favors protected request bodies or similarly bounded interfaces.

Django:

1. authenticates session and resolves current Workspace Grant;
2. validates query encoding/length/options and rate limits;
3. selects the active projection version;
4. scopes candidates to the Workspace and eligible lifecycle;
5. ensures projection source Revision/version equals authoritative current state;
6. applies PostgreSQL full-text query/matching/ranking;
7. limits result count/work;
8. creates safe snippets after authorization/version validation;
9. returns stable Scene/current-Revision references and bounded metadata; and
10. logs only privacy-safe performance/outcome categories.

Search result selection cannot authorize the subsequent Scene read. Opening a result performs ordinary record authorization/current lookup again.

Malformed/expensive queries fail safely without exposing SQL, configuration, record existence, snippets, or internals. Empty/stop-word-only queries receive defined bounded behavior later.

## Workspace Scoping and Authorization

Every projection directly carries Workspace scope. Projection-to-Scene/Revision relationships must be same-Workspace through constraints where feasible and service validation always.

Queries filter Workspace before returning ranks/snippets/counts. Unauthorized records cannot influence visible counts, facets, timing, snippets, spelling hints, or “no result” details in a way that confirms existence.

Projection UUID, Scene UUID, rank, headline marker, query token, index row, result position, and search Job ID confer no permission.

Workers re-resolve current service authority and source Workspace before building/publishing. Indexing a record once does not authorize future search after Grant/lifecycle/source changes.

Global cross-Workspace search is outside Version 1. Future multi-Workspace search requires explicit authorization and privacy design, not removal of Workspace filters.

## Lifecycle and Eligibility

Lifecycle determines whether an otherwise authorized record participates in a search scope; it does not replace authorization.

- Active Scenes are eligible for ordinary search.
- Archived Scenes are excluded from the default active view but may be included through an explicit authorized archived filter.
- Trashed Scenes are excluded from ordinary search by default and require a future deliberate trash/recovery view rather than a generic search toggle.
- Purged Scenes have no authoritative source and projections are cleaned only after authoritative purge policy permits it.
- Restored Scenes are reindexed from current authoritative state.

Lifecycle transition advances Scene version/invalidates projection and dispatches rebuild or removal. A stale projection for a trashed record is not returned.

Content state, contextual Canon, provenance, and later record type may become explicit filters/ranking inputs only after their authoritative schema/query semantics exist. Index labels never promote authority.

## Ranking and Matching

PostgreSQL full-text search provides lexeme matching and ranking. Version 1 may weight title differently from body and later bounded fields, but exact weights/configuration are deferred.

Rank:

- orders candidates for one query/configuration;
- is not probability, truth, importance, Canon, quality, chronology, recency, or authorization;
- may change after PostgreSQL/configuration/reindex changes;
- is not exported as durable creative metadata; and
- is not used to infer AI context permission.

Trigram-assisted matching may later improve misspellings/prefix/name search if a supported PostgreSQL extension/configuration is justified, measured, and privacy-reviewed. It is not required by this ADR.

Database `LIKE/ILIKE` may support bounded fallback/admin diagnostics or simple exact fields, but is not the primary full-text strategy. Semantic similarity/vector search remains out of scope.

Query parsing, prefix behavior, phrase support, field weights, language selection, dictionaries, stemming, stop words, typo tolerance, and tie-breaking remain later decisions.

## Snippets and Excerpts

Search snippets are derived private content produced only after candidate Workspace/lifecycle/freshness authorization.

Version 1 prefers query-time generation from the current valid projection or exact authoritative current content under the same version check. This avoids storing many query-specific text fragments and stale highlights.

Snippets:

- are bounded in size/count;
- preserve Unicode boundaries;
- escape manuscript text and mark highlights with application-controlled safe structure;
- never trust stored/provider/manuscript text as HTML;
- do not reveal neighboring content beyond the authorized bounded excerpt;
- carry source Scene/current Revision references; and
- are not logged, indexed again, exported as authority, or treated as provenance.

If query-time highlighting is too costly, a future derived excerpt cache may be added with source/query/configuration version, strict retention, and the same privacy rules. Stored generic excerpts are not selected initially.

Search summaries/counts are similarly derived/advisory and must identify their algorithm/source version where retained.

## Search Normalization and Versioning

Authoritative content normalization under ADR-0006 is complete before search. Search derives tokens/lexemes without changing the Revision content.

Search configuration/version covers:

- selected PostgreSQL text-search configuration/language behavior;
- title/body/metadata field composition;
- tokenization and stemming/dictionaries;
- stop-word behavior;
- field weights/ranking formula version;
- optional trigram behavior;
- snippet/highlighting algorithm version; and
- projection schema version.

These versions are independent of Django migration number, archive version, content-format version, and content-normalization version, though compatibility metadata may relate them.

Changing search configuration requires new projection version/reindex. It does not rewrite Scene Revision, change Scene version merely because an index algorithm changed, or create Mutation Operation creative provenance.

The same authoritative source and search-version should produce semantically repeatable projection inputs, but exact rank/token output may vary across supported PostgreSQL versions and must be verified during upgrades.

## Rebuild and Reindex

**Rebuild** recreates the active projection version after loss, corruption, restore, or missing data. **Reindex** generates a new projection/search version because schema/tokenizer/ranking behavior changed.

Full rebuild procedure:

- enumerate authorized authoritative sources by Workspace using stable IDs;
- create bounded idempotent Jobs/batches;
- build current projections from explicit pointers/versions;
- conditionally publish only matching current state;
- track bounded progress/counts/errors without content;
- detect missing/extra/stale projections;
- remove/retire projections with no eligible authoritative source; and
- verify search usability/authorization after completion.

Version migration prefers dual-version build and cutover:

1. declare new target projection version inactive;
2. build it alongside current serving version;
3. validate counts/freshness/authorization/representative queries;
4. atomically/configurationally select one active serving version;
5. preserve rollback to prior version for a bounded period; and
6. clean old projections only after evidence/retention permits.

One in-place destructive rewrite is rejected as the normal migration because partial failure can leave no usable index. Authoritative data remains safe either way.

External search migration later follows the same parallel build/validate/cutover and can always rebuild from PostgreSQL.

## Failure and Stale-Index Behavior

Indexing failures never roll back a committed Scene save or make projection data authoritative.

Failure categories include missing/inaccessible source, Workspace mismatch, stale version, unsupported projection/content version, invalid Unicode/configuration, database transient failure, lease/cancellation, resource limit, and projection write conflict.

- Stale source during build: discard and enqueue/allow current build.
- Transient database/worker failure: retry within ADR-0010 budgets.
- Authorization/Workspace mismatch: terminal/security-safe failure.
- Unsupported configuration/version: quarantine/reindex decision.
- Cancellation: stop at safe checkpoint; old projection remains invalid if source changed.
- Missing projection: omit source from search and expose bounded index-health status to authorized owner/operator.

Search queries do not serve a known-stale projection as current. They may omit affected records and optionally show a generic “search is updating” state without revealing which inaccessible records are pending.

If search is unavailable/corrupt, ordinary direct navigation/editing/export/backup remains available. Search failure never changes Scene/Revision/Link/provenance state.

No automatic “repair” rewrites domain content to fit the index.

## Restore and Recovery Reconciliation

Database backups may contain projection rows/search indexes for speed, but they are untrusted derived state after recovery. Structured archives need not contain them.

Normal restoration:

1. restore and verify authoritative records first;
2. disable serving restored projections initially or validate active version explicitly;
3. invalidate/quarantine restored unfinished indexing Jobs/leases;
4. compare projection source Workspace/Scene/Revision/version against authoritative state;
5. discard projections by default when compatibility/freshness is uncertain;
6. regenerate bounded rebuild Jobs under ADR-0010 rather than resume old attempts;
7. validate Workspace isolation, counts, lifecycle eligibility, freshness, representative matching/snippets, and no content leakage; and
8. enable search only when a serving projection version is verified.

Rebuild is not restoration: restoration recovers authoritative archive; rebuild derives query state afterward. Search availability may lag recovery activation if direct authoring/navigation remains safe and status is clear.

Point-in-time recovery can restore projections and Jobs from different logical moments; explicit source-version validation prevents their use.

Same-archive restoration preserves source UUIDs, enabling deterministic projection references. Cross-Workspace import receives new source IDs and builds new projections; imported projection IDs are never trusted.

## Retention and Cleanup

Current active projections are retained while their source is eligible. Old projection versions, failed build artifacts, query-specific transient snippets, Jobs/Attempts, and telemetry follow bounded separate policies.

Cleanup:

- is a bounded idempotent Job/operation;
- removes projections only after verifying source/current active version/cutover state;
- cannot cascade to Scene, Revision, Link, Mutation Operation, provenance, archive, or backup;
- preserves rollback version until cutover evidence/period permits removal;
- handles trashed/purged sources according to lifecycle/purge policy;
- does not treat projection absence as authorization to delete source; and
- records bounded counts/status, not private content.

Structured archives omit projections by default. Database backups may retain old projections until backup expiry; this does not make them current after restore.

Exact retention periods, cleanup cadence, batch size, failed-projection evidence, and archive inclusion remain later operational decisions.

## Privacy, Logging, and Telemetry

Search queries, snippets, result titles, result clicks, no-result terms, and derived documents are private content/behavior. They are not broadly retained by default.

Routine telemetry may record:

- timestamp;
- operation/search type;
- active projection/configuration version;
- bounded query-length bucket, not query text;
- result-count bucket;
- latency;
- stale/missing/lag counts;
- Job/rebuild state/counts;
- safe error category; and
- non-secret correlation ID.

It excludes raw query, lexemes if story-derived, titles, snippets, manuscript text, stable private record IDs when unnecessary, URLs/query strings, credentials, sessions, MFA state, provider secrets, Job payloads, SQL, and exception locals.

Security events record authorization abuse/rate-limit/admin reindex actions with bounded categories, not search content. Query analytics require a separate privacy decision and owner value justification.

Search endpoints enforce query/result/complexity/rate/concurrency limits to resist denial of service. Errors avoid confirming inaccessible records or exposing configuration/SQL.

## Django Application Boundary

Django services own query validation, Workspace/grant resolution, lifecycle eligibility, active projection version, freshness checks, result authorization, snippet escaping, rate limits, indexing dispatch, rebuild/cutover, and privacy-safe status/errors.

Workers call scoped query/projection services under bounded service identity. They do not mutate authoritative Scene/Revision/Link state or infer current records from projection rows.

Django's PostgreSQL search integration may express search queries/vector/rank/headline operations, but the exact APIs/version are implementation details. ORM convenience does not replace database constraints or authorization.

Browser route hiding is not search authorization. Result opening rechecks the authoritative record.

No models, migrations, APIs, templates, Jobs, indexes, SQL, or packages are created by this ADR.

## PostgreSQL Boundary

PostgreSQL stores authoritative domain records and rebuildable search projections. Native full-text capabilities provide searchable vectors/documents, query parsing, ranking, highlighting, and indexes selected later.

PostgreSQL should reinforce:

- projection UUID uniqueness;
- direct Workspace/Scene/Revision same-scope references;
- one projection per source/projection version where required;
- constrained projection state/version;
- source version/revision metadata non-nullness;
- active-version/cutover consistency where row-local; and
- protective/non-cascading source relationships.

Query execution joins/filters authoritative Scene/lifecycle/current-pointer/version as needed to prevent stale/private results. Database indexes optimize matching but do not authorize.

Exact `tsvector` composition/storage, generated columns, expression indexes, GIN/GiST/trigram extensions, text-search configuration, dictionaries, ranking/headline functions, index definitions, and query plans remain later physical design.

PostgreSQL full-text search is selected as the initial mechanism, not a permanent prohibition on external search after measurement.

## Rationale

PostgreSQL-native search fits the modular monolith, avoids another external service/failure/privacy boundary, and can enforce Workspace/source relationships near authoritative state.

One current-Scene projection makes validity explicit and keeps current search separate from immutable revision history. Exact source Revision/version fields let queries detect stale data immediately.

Hybrid invalidation and asynchronous rebuild preserve save durability/latency while making lag bounded and honest. Known-stale omission avoids displaying obsolete manuscript excerpts as current.

Versioned rebuildable projections allow schema/tokenizer changes, restore, and future external search migration without rewriting domain records. Query-time snippets reduce persistent private duplicates.

Privacy-safe telemetry and strict authorization prevent search from becoming an enumeration/logging side channel.

## Decision Criteria

Options are evaluated against:

1. preservation of authoritative Scene/Revision identity;
2. Workspace isolation and result/snippet authorization;
3. freshness detectability and honest lag behavior;
4. save latency/failure isolation;
5. complete rebuild after loss/restoration;
6. ranking/snippet usefulness without authority confusion;
7. privacy of manuscripts/queries/clicks;
8. lifecycle correctness;
9. migration/version/cutover safety;
10. maintainability for one owner/modular monolith;
11. bounded Job/retry/recovery semantics;
12. future search-engine portability; and
13. avoidance of premature semantic/vector complexity.

## Alternatives Considered

### No search in Version 1

Rejected because scope/acceptance requires finding Scenes and supported entities; navigation alone becomes inadequate.

### Database LIKE or ILIKE only

Simple but limited ranking/tokenization/index behavior and can become expensive. Useful only for bounded exact/simple fallback.

### PostgreSQL full-text search

Selected. It provides integrated indexing/ranking/highlighting without an external source of truth.

### Trigram-assisted search

Deferred optional complement for names/typos after measurement; not the primary decision.

### External search engine

Rejected for V1 due to another service, synchronization/privacy/authorization/recovery complexity without measured need.

### Semantic or vector search

Rejected/out of scope. It introduces embeddings/provider/context/meaning/privacy costs and requires a separate ADR.

### Fully synchronous indexing

Strongest immediate consistency but couples save latency/failure/locks to derived work. Rejected default.

### Fully asynchronous indexing without synchronous invalidation

Fast saves but old projections can appear current until worker runs. Insufficient.

### Hybrid invalidation plus asynchronous rebuild

Selected. Old source version becomes detectably invalid immediately; worker builds later.

### Search current Revision directly on every query

Always current and simple initially but repeated tokenization/ranking may be expensive and offers weak explicit version/rebuild semantics. Not primary.

### Materialized current-Scene projection

Selected.

### One projection per Scene

Selected per projection version for current search.

### One projection per Revision

Useful for historical-revision search but multiplies sensitive index data and is outside V1 current-content search.

### Serve stale projections

Rejected as default because obsolete text may mislead and leak lifecycle-deleted content.

### Omit stale results

Selected with bounded updating status.

### Block saves until indexing succeeds

Rejected because derived failure must not roll back authoritative work.

### Save succeeds with later indexing

Selected.

### Store snippets

Rejected initially due to query-specific staleness/privacy duplication.

### Generate snippets at query time

Selected after freshness/authorization.

### Include trashed Scenes

Rejected in ordinary search.

### Exclude trashed Scenes

Selected.

### Include archived Scenes by default

Rejected to keep active search focused.

### Archived filter

Selected as later explicit authorized search option.

### Raw query logging

Rejected due to manuscript/private-interest leakage.

### Privacy-safe bounded telemetry

Selected.

### Structured archive includes projections

Rejected by default because projections are rebuildable/version-specific.

### Projections rebuilt after restore

Selected normal path.

### One in-place projection version

Simple but partial migration can leave search unusable. Rejected normal reindex.

### Dual-version rebuild and cutover

Selected for configuration/schema migrations.

### PostgreSQL queue indexing

Selected through ADR-0010 Jobs.

### Direct synchronous update

Allowed only if later evidence shows a bounded trivial projection; rejected default for body full-text indexing.

### External broker dispatch

Not selected; future broker may deliver ADR-0010 Job IDs without changing semantics.

### External search now

Rejected.

### Defer external search until measured need

Selected.

## Comparative Assessment

### Search engine strategy

| Strategy | Capability | Operations/privacy | Rebuild | Decision |
| --- | --- | --- | --- | --- |
| No search | None | Lowest | N/A | Rejected |
| LIKE/ILIKE | Basic substring | Low | Direct | Insufficient primary |
| PostgreSQL FTS | Strong V1 text search | Low/moderate | Integrated | Selected |
| External engine | Strong/scalable | High | Sync required | Deferred |
| Vector/semantic | Semantic | Highest/provider-sensitive | Complex | Out of scope |

### Projection shape

| Shape | Freshness evidence | Storage | Decision |
| --- | --- | --- | --- |
| Query source every time | Immediate | Low | Not primary |
| One current projection/Scene/version | Explicit | Moderate | Selected |
| Every Revision projection | Strong historical | High/private duplication | Deferred |
| Generic unversioned document | Weak | Moderate | Rejected |

### Indexing timing

| Timing | Save latency | Freshness | Failure isolation | Decision |
| --- | --- | --- | --- | --- |
| Fully synchronous | Higher | Immediate | Weak | Rejected default |
| Async only/no marker | Low | Unknown/stale window | Strong | Insufficient |
| Sync invalidation + async build | Low | Detectable lag | Strong | Selected |

### Stale-index behavior

| Behavior | User completeness | Correctness/privacy | Decision |
| --- | --- | --- | --- |
| Serve stale silently | High | Poor | Rejected |
| Serve with marker | Higher | Risky excerpts | Deferred |
| Omit stale + updating state | Temporary omission | Strong | Selected |
| Block all search | Low availability | Strong | Too broad |

### Snippet strategy

| Strategy | Freshness | Storage/privacy | Cost | Decision |
| --- | --- | --- | --- | --- |
| Stored static snippets | Can stale | More copies | Low query | Rejected initial |
| Query-time from valid projection | Current-checked | Minimal persistence | Query cost | Selected |
| No snippets | N/A | Lowest | Lowest | Insufficient UX |

### Lifecycle eligibility

| Lifecycle | Default search | Optional view |
| --- | --- | --- |
| Active | Included | Yes |
| Archived | Excluded | Authorized filter |
| Trashed | Excluded | Future trash/recovery view |
| Purged | No source/projection | None |

### Restore behavior

| Strategy | Recovery speed | Trust | Decision |
| --- | --- | --- | --- |
| Serve restored projections immediately | Fast | Weak | Rejected default |
| Validate and reuse | Moderate | Conditional | Optional optimization later |
| Discard/rebuild | Slower | Strong | Selected normal path |
| Import projections from archive | Fast | Version/cross-scope risk | Rejected |

### Reindex/version migration

| Strategy | Availability | Rollback | Decision |
| --- | --- | --- | --- |
| In-place rewrite | Risky | Weak | Rejected normal path |
| Drop then rebuild | Outage | Moderate | Not preferred |
| Dual build/validate/cutover | Strong | Strong | Selected |

### Privacy and telemetry

| Strategy | Diagnostic value | Privacy | Decision |
| --- | --- | --- | --- |
| Raw queries/snippets/clicks | High | Poor | Rejected default |
| No metrics | Low | Strong | Insufficient operations |
| Bounded buckets/categories | Strong enough | Strong | Selected |

## Evidence

### Repository evidence

- Product vision/scope require search and navigation across private creative records.
- Product principles require privacy, navigable connections, authorial control, and narrow Version 1.
- Architecture overview defines search as server-coordinated and derived indexes as rebuildable.
- Data model requires Scene/Character/Location search, explicit Workspace scope, authoritative Links, derived backlinks, and excludes semantic search.
- Security architecture requires authorization on every search, no private queries/snippets in logs, and denial-of-service controls.
- ADR-0001 through ADR-0011 establish Django/PostgreSQL, UUIDs, explicit current revisions, normalized content, derived boundaries, Jobs, restoration, and no AI/vector retrieval authority.
- Architecture handoff records search/derived projection as a dependency-aware next ADR.
- Story Engine audit recommends preserving fast search/snippets while replacing its missing Workspace/state/freshness boundaries.

### Official guidance reviewed conceptually

- [PostgreSQL Full Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [PostgreSQL text-search controls/configuration](https://www.postgresql.org/docs/current/textsearch-controls.html)
- [PostgreSQL tables and indexes for text search](https://www.postgresql.org/docs/current/textsearch-tables.html)
- [PostgreSQL ranking search results](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-RANKING)
- [PostgreSQL highlighting results](https://www.postgresql.org/docs/current/textsearch-controls.html#TEXTSEARCH-HEADLINE)
- [Django PostgreSQL full-text search](https://docs.djangoproject.com/en/stable/ref/contrib/postgres/search/)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)
- [OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)

This guidance supports PostgreSQL-native text search, explicit configurations, suitable indexes, ranking/highlighting as derived query behavior, server authorization, bounded queries, and privacy-safe logs/errors.

### Evidence still required

Before implementation:

- confirm initial searchable record types/fields as physical schemas arrive;
- select supported PostgreSQL/Django versions and text-search capabilities;
- define projection schema/search-normalization versions;
- compare stored search vector/document/expression approaches;
- measure synchronous invalidation and async build latency with synthetic Scenes;
- define conditional publish/idempotency/duplicate Job behavior;
- set lifecycle/default archived filters;
- select language/tokenizer/dictionary/stemming/stop-word behavior;
- define ranking/field weights/tie-breaking and query syntax;
- assess optional trigram support for names/typos;
- define snippet escaping/highlighting/limits;
- define query/result/rate/complexity limits;
- define active-version dual-build/cutover/rollback;
- define restore discard/rebuild and search-readiness criteria;
- define bounded telemetry/retention/cleanup; and
- test authorization, stale omission, restore, migration, Unicode, performance, and privacy with synthetic content.

## Consequences

### Positive

- No external search service or provider privacy boundary is required.
- Explicit source revision/version makes stale projections detectable.
- Saves remain durable even when indexing fails.
- Known-stale excerpts are not presented as current.
- Full rebuild depends only on authoritative PostgreSQL records.
- Projection versions permit safe search changes without domain migration.
- Query-time snippets reduce stored private duplicates.
- Workspace/lifecycle authorization is enforced at query and result-open time.
- Restore can discard potentially corrupt indexes confidently.
- Future external search can adopt the same semantics after measurement.

### Negative

- Recently changed Scenes may be temporarily absent from search.
- PostgreSQL carries indexing, queue, and query load alongside authoritative traffic.
- Projection tables duplicate some private text.
- Conditional freshness joins/checks add query/schema complexity.
- Dual-version rebuild temporarily doubles projection storage/work.
- Language/tokenization/ranking behavior may not satisfy every creative name/style.
- Query-time snippets add computation.
- Conservative lifecycle/stale filtering may produce fewer results.
- Search health/rebuild status requires operational UI/metrics.
- Future external migration still requires parallel build/validation.

### Neutral or Operational

- Exact rank is intentionally unstable across configurations.
- Database backups may include projections; portable archives need not.
- Search version differs from schema/content versions.
- Trigram support may be added later without changing authority.
- Character/Location projections follow after their physical schema.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Projection served after Scene change | Stale/private text leak | Source Revision/version checks and sync invalidation | Query bugs remain possible |
| Indexing failure hides Scene | Search omission | Job retry/status/full rebuild; direct navigation remains | Owner may not notice immediately |
| Worker overwrites newer projection | Stale result | Conditional publish on current source/version | Complex races require tests |
| Workspace filter omitted | Cross-Workspace disclosure | Direct Workspace, constraints, scoped services, adversarial tests | App regressions remain possible |
| Trashed Scene remains searchable | Deleted-content exposure | Lifecycle invalidation and query join/filter | Index lag must be detected |
| Query logs leak story terms | Privacy breach | No raw query logging; bounded telemetry | Debug misconfiguration risk |
| Snippet markup causes XSS | Browser compromise | Escape text/application-controlled highlights | Rendering bugs remain possible |
| FTS query causes DoS | Availability impact | Length/complexity/rate/result limits and indexes | Pathological queries remain |
| PostgreSQL queue/search affects saves | Latency | Async build, workload measurement, bounds | Shared database contention |
| Search configuration changes ranks | User confusion | Version/cutover/communication/tests | Ranking remains heuristic |
| Language stemming harms names | Missed/false matches | Test representative synthetic language; field-specific rules | Creative language is unusual |
| Dual build incomplete | Wrong cutover | Validate counts/freshness before activation; rollback | Large rebuild may be slow |
| Restore trusts old projections | Corrupt/stale search | Disable/discard/rebuild normal path | Search unavailable during rebuild |
| Backlinks diverge from Links | Navigation inconsistency | Authoritative Link wins; rebuild/verification | Temporary lag possible |
| Projection cleanup cascades | Data loss | Protective references/no domain cascade | Privileged SQL risk |
| External search later becomes source | Lock-in/authority drift | ADR invariant and rebuild tests from PostgreSQL | Operational dependence can grow |
| Raw clicks retained | Behavioral privacy loss | No broad click analytics by default | Browser/server access logs may reveal paths |
| Missing projection mistaken for missing record | UX confusion | Separate search-updating/health state | Result completeness remains uncertain during lag |
| Archived filtering misleads | Incomplete discovery | Explicit archived filter/status | Default choice may surprise |
| Search used to select AI context automatically | Privacy expansion | ADR-0011 explicit manifest/approval; search discovery not permission | Feature integration bugs remain |

## Security and Privacy Review

- Security-sensitive: Yes; search processes and returns private manuscript text.
- Primary references: `docs/architecture/security.md`, `docs/architecture/data-model.md`, ADR-0001 through ADR-0011.
- Additional references: product docs, architecture overview, AI context, integrations, architecture handoff, and Story Engine audit.

### Assets and trust boundaries

Assets include authoritative Scenes/Revisions, projections/vectors, queries, snippets, result identities, lifecycle state, Jobs, indexes, telemetry, and restored data. Browser queries/results and worker projection builds cross trust boundaries.

### Authorization and enumeration

Django enforces Account/Grant/Workspace/lifecycle authorization before candidate disclosure and again when opening results. Counts, snippets, timing, facets, correction suggestions, and index-health detail must not expose inaccessible records.

### Private duplicated content

Projection text/search vectors and snippets are private derivative copies. Database roles, backup, retention, deletion, incident response, and environment separation protect them. Derived does not mean low sensitivity.

### Input/output safety

Queries are untrusted input and use typed PostgreSQL search interfaces, not string-interpolated SQL. Snippets are untrusted content and escaped. No query/result becomes code, path, URL authority, template, SQL, AI instruction, or provider request permission.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- unauthenticated/cross-Workspace/altered-ID searches and counts;
- active/archived/trashed eligibility transitions;
- source change immediate stale detection before Job completes;
- duplicate/stale worker conditional publication;
- indexing failure without save rollback;
- Job retry/cancellation/lease/restore quarantine;
- missing/stale projection omission and health state;
- query length/complexity/rate/result/timeout limits;
- Unicode, punctuation, invented names, stemming, stop words, and language behavior;
- rank non-authority and deterministic tie behavior where needed;
- snippet Unicode boundaries, escaping, highlight safety, and privacy;
- raw query/snippet/title/content absence from logs/metrics/errors/URLs/security events;
- full rebuild from authoritative data only;
- dual-version build/validation/cutover/rollback;
- database restore discard/rebuild and structured archive omission;
- backlink authoritative-source disagreement/repair; and
- no search/AI integration broadening context automatically.

### Residual risk

Search necessarily duplicates/processes private text in PostgreSQL and returns excerpts to authorized browsers. A compromised application/database/owner device exposes it. Tokenization/ranking can miss relevant material or rank misleadingly. Timing/count side channels and operational logs require ongoing review. Shared PostgreSQL search load can affect authoritative operations.

## Product and Architecture Alignment

### Product alignment

The decision makes existing material findable and connections navigable while preserving privacy, authorial control, stable identity, and rebuildable ownership.

### Scope alignment

It supports Version 1 text search/navigation without semantic search, embeddings, recommendations, external vendors, or autonomous retrieval.

### ADR alignment

- ADR-0001: browser search is server-mediated.
- ADR-0002: search remains in the Django modular monolith.
- ADR-0003: PostgreSQL is authoritative and derived indexes rebuild.
- ADR-0004: explicit current Revision/version define searchable content.
- ADR-0005: every query/result is current-account/Workspace authorized.
- ADR-0006: projection derives from normalized text without rewriting it.
- ADR-0007: projections/backlinks remain separate supporting records.
- ADR-0008: UUID/Workspace constraints and physical-schema boundaries guide projection tables.
- ADR-0009: structured archives omit rebuildable projections; restoration verifies/rebuilds.
- ADR-0010: indexing uses durable Jobs/idempotency/retry/quarantine.
- ADR-0011: search discovery does not itself authorize AI context or retrieval.

### Architecture alignment

The model implements server-side search, derived/backlink rebuildability, privacy-safe telemetry, authoritative source references, and provider-independent recovery.

### Normative-document impact

If accepted, overview, data-model, security, backup/restoration, job, and AI-context documents should be reconciled with current-Scene projections, hybrid indexing, stale omission, lifecycle filters, query-time snippets, and dual-version rebuild. The ADR index should be updated. No implementation is authorized.

## Migration and Portability

Projection semantics—source Workspace/record/revision/version, projection/configuration version, lifecycle eligibility, freshness, and rebuildability—remain portable even if search-engine syntax changes.

PostgreSQL version/configuration upgrades require representative query/rank/highlight tests and versioned reindex where behavior changes. They do not rewrite authoritative records.

A future external search engine receives derived Workspace-scoped documents through Jobs, builds in parallel, validates against PostgreSQL, and cuts over one serving version. Disconnection/loss triggers rebuild without domain loss.

Structured archives preserve authoritative source fields, not projections. Same-archive restoration rebuilds using preserved UUIDs. Cross-Workspace import creates new IDs and new projections.

Migration rollback retains authoritative data and at least one valid serving projection version where feasible. Failure can disable search temporarily but cannot corrupt Scenes/Revisions.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Define initial searchable record types/fields as physical domain tables are introduced.
- [ ] Select supported Django/PostgreSQL versions and evaluate native search APIs.
- [ ] Define projection and search-normalization version schemas.
- [ ] Define synchronous invalidation and commit-coupled indexing Job payload.
- [ ] Define conditional publish/idempotency/freshness queries.
- [ ] Define active/archived/trashed eligibility and filters.
- [ ] Select/test language configuration, tokenization, dictionaries, stemming, stop words, and optional trigram behavior.
- [ ] Define title/body/metadata weighting and rank/tie behavior.
- [ ] Define query parsing, size/complexity/rate/result limits.
- [ ] Define query-time snippet/highlight escaping and limits.
- [ ] Define index-health/freshness/lag owner status and bounded metrics.
- [ ] Define full rebuild batching, priority, cancellation, and verification.
- [ ] Define dual-version reindex/cutover/rollback/cleanup.
- [ ] Define backup/restore discard/rebuild/readiness procedure.
- [ ] Define backlink projection contract when authoritative Link schema is accepted.
- [ ] Add later unit/integration/concurrency/security/privacy/migration/restore/performance tests using synthetic data.
- [ ] Evaluate external search only after measured PostgreSQL limits justify it.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes application code, Django initialization, models, migrations, SQL, indexes, extensions, database objects, Jobs, commands, search APIs/templates, tests, packages, PostgreSQL configuration, external search vendors, vector databases, embeddings, semantic search, deployment, modification of the old Story Engine, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No application code, model, migration, SQL, index, extension, database object, Job, command, search code, template, API, test, package, PostgreSQL search configuration, vendor, ranking weight, tokenizer, dictionary, stemmer, stop-word list, trigram threshold, polling interval, rebuild schedule, retention period, or index size is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
