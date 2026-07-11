# ADR-0013: Import, Legacy Story Engine Migration, and Identity Mapping

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 boundaries for staged import, legacy Story Engine migration, untrusted source artifacts, source validation and classification, new Strange Novelty identity assignment, source-to-target mapping, revision reconstruction, lifecycle and ordering transformation, provenance, duplicate and conflict handling, dry runs, human approval, bounded all-or-nothing application, Jobs and idempotency, rollback and reversal, privacy, retention, and recovery reconciliation, while exact supported source formats and Story Engine versions, parser libraries and isolation, Batch/staging/mapping/report schemas, source-field mappings, snapshot and current-state reliability rules, normalization details and limits, duplicate-detection heuristics, lifecycle and ordering mappings, transaction-size bounds, checkpoint/compensation design, attachment handling, retention periods, archive inclusion, database constraints and indexes, review interface, and deployment configuration remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; domain migration, Django, PostgreSQL, security, privacy, revision/history, provenance, jobs, backup/restoration, and legacy-data perspectives

## Context

Strange Novelty may need to bring selected creative material from the old Story Engine or other external artifacts into the first private Workspace. The source system is not current Canon, is not an authority boundary, and does not share Strange Novelty's identity, revision, Workspace, provenance, lifecycle, authorization, or recovery model.

The Story Engine audit found local integer IDs, no Workspace identity, direct in-place Chapter updates, selective snapshots, inconsistent status concepts, many story-specific tables, name-based matching, partial item-by-item import, browser-side/provider-assisted parsing, settings mixed with credentials, incomplete exports, and no verified restoration contract. These observations are evidence for a careful mapping—not authorization to access the old database, run old code, reuse schemas, or import everything.

ADR-0001 through ADR-0012 establish the target invariants. Django mediates untrusted input. PostgreSQL stores authoritative state. New imported records receive application-generated UUIDs. Scene Revision stores immutable normalized plain-text snapshots. Current pointer/version, lifecycle, sparse ordering, Mutation Operation provenance, Jobs/idempotency, archive/restoration, AI Suggestion boundaries, and rebuildable search remain intact.

Import differs fundamentally from same-archive restoration. Restoration proves the same archive and preserves UUIDs exactly. Import creates new target identities, stages evidence, requires owner review, and never inherits source Account grants, sessions, credentials, provider secrets, Canon, approval, or permissions.

The decision must distinguish:

- import from restoration, archive migration, repair, and author editing;
- source identity from target identity;
- identity mapping from authorization;
- duplicate detection from merge;
- content equality from record identity;
- dry run from apply;
- staging from authoritative state;
- validation from approval;
- approval from execution;
- transformed content from exact source evidence;
- source normalization from target normalization;
- reconstructed history from fabricated history;
- legacy sequence from Strange Novelty revision number;
- source current state from target current pointer;
- Import Batch from Job and Mutation Operation;
- idempotency from identity mapping;
- retry from re-import;
- cancellation from rollback;
- rollback from restoration;
- omission from deletion;
- unsupported data from malformed data;
- warning from failure;
- source metadata from secrets;
- import report from logs; and
- source ownership claims from target Workspace authority.

This ADR neither accesses `/home/burmuss/projects/the-story-engine` nor any source/current database. It selects no parser library, source schema, import script, database connector, package, or implementation.

## Decision

If accepted, Version 1 will use the following architecture.

1. Treat every import, including Story Engine migration, as an explicit one-way staged transformation into one authorized target Workspace. Never attach the legacy database as an ongoing live source.
2. Accept only allowlisted, versioned source formats through server-side parsers. Source artifacts, archives, databases, paths, links, and serialized values are untrusted.
3. Create a durable Import Batch with stable UUID, target Workspace, source-system/type/version/checksum evidence, parser/transformation version, Job/idempotency references, state, counts, validation/report references, owner approval, and timestamps.
4. Create staged item and identity-mapping records before authoritative writes. Each source entity receives a newly generated Strange Novelty UUID; legacy IDs remain bounded source provenance only.
5. Source-to-target mapping is unique within source scope/import batch and records source type/ID/version/fingerprint, target type/new UUID, parent/relationship mappings, disposition, and transformation version. Mapping never grants authority.
6. Do not use title, timestamp, source sequence, ordering, path, content hash, or similarity as authoritative identity. They may produce duplicate warnings only.
7. Never automatically merge or overwrite existing records. Import into a non-empty Workspace is permitted only through explicit staging and conflict review. Prefer a new or explicitly selected target Workspace.
8. Parse, validate, classify, transform, map, detect duplicates/conflicts, and preview in staging. No authoritative record is created during dry run.
9. Imported creative material starts as Imported content unless an explicit later owner action changes state. Source Canon/approval/status never automatically becomes target Canon or approval.
10. Normalize imported Scene content under ADR-0006 only when producing a proposed target value. Preserve source bytes/text evidence separately where policy permits and report all representation transformations, including encoding/line-ending changes.
11. For legacy Scene/Chapter history, import trustworthy source current content and trustworthy snapshots as separate immutable imported revisions in validated source order. Do not fabricate missing revisions or infer precise chronology from unreliable timestamps.
12. Target revision UUIDs and display revision numbers are newly allocated. Source snapshot IDs/numbers/timestamps remain provenance evidence.
13. Select target current content through an explicit source-specific validated rule and owner preview. Never infer it solely from newest timestamp or highest source number when semantics are uncertain.
14. Map lifecycle and ordering through explicit versioned rules. Unknown lifecycle states require owner classification or fail. Archived/trashed source records never silently become active. Source positions transform deterministically into target sparse ordering with collision/missing-position warnings.
15. Unsupported but well-formed data is inventoried and reported; bounded source metadata may be retained. Malformed/hostile data fails safely. Semantically important missing relationship targets are reported rather than silently dropped.
16. Credentials, keys, settings, sessions, cookies, MFA/recovery state, provider secrets, deployment configuration, old permissions, and source grants are excluded absolutely.
17. External paths, URLs, symlinks, attachments, executables, macros, scripts, plugins, SQL, templates, and embedded instructions are never followed or executed automatically. Unsupported attachments are inventoried and reported.
18. Import application revalidates owner/Grant/Workspace, source artifact integrity, Batch/mapping/transformation versions, target conflicts/current state, and explicit approval.
19. Prefer bounded full-batch all-or-nothing application in one controlled transaction for Version 1. If representative size exceeds safe transaction bounds, do not silently switch to partial application; define durable checkpoints/compensation in a later ADR.
20. Application creates ordinary target records through accepted services. Imported Scene content/history creates immutable Revisions, current pointer/version, lifecycle/order, and Mutation Operation provenance without bypassing constraints.
21. Use batch-level durable idempotency and unique source mappings so duplicate Job delivery/retry converges. Same key/source fingerprint returns/reconciles prior staging/application; changed fingerprint fails visibly.
22. Cancellation before apply discards/stops staging safely. Cancellation during atomic apply takes effect only before commit/at safe checkpoints; it is not rollback of committed records.
23. Post-apply reversal is a separate protected plan, not “undo import,” and cannot delete unrelated target data or rewrite immutable history. Staging deletion never cascades to applied domain records.
24. Import Jobs follow ADR-0010. Restored unfinished imports are quarantined and revalidated/reconciled; they never resume or apply blindly.
25. Source artifacts, raw staging content, previews, reports, and mappings receive bounded retention/privacy protection. Exact periods remain later policy.

## Terminology and Boundaries

**Import** transforms external/source material into a target Workspace with new Strange Novelty identities. **Restoration** reconstructs the same archive and preserves identities. **Archive migration** converts a supported archive version. **Repair** fixes exceptional target corruption. **Author editing** is an ordinary creative mutation.

A **source artifact** is the protected untrusted input package/file/database copy/export. An **Import Batch** describes one staged import operation. A **staged item** is a parsed/transformed proposal. An **identity mapping** links a source identity to a newly assigned target identity.

A **dry run** validates/transforms/reports without authoritative writes. **Apply** commits approved target records. Successful validation proves structural compatibility, not owner approval or truth.

A **duplicate candidate** is evidence of possible overlap. **Merge** combines identities/content and is never inferred automatically. Equal content hashes prove byte/content equality under one algorithm, not record identity.

**Source evidence** preserves what was observed. **Transformed content** is the proposed target representation. Target normalization does not rewrite the source artifact.

**Reconstructed history** uses explicit trustworthy snapshots/order/current evidence. **Fabricated history** invents missing states or exact chronology; it is prohibited.

**Rollback** of an uncommitted transaction leaves no target records. **Reversal** after commit is a new protected operation. **Restoration** is not either one.

## Import Architecture Principles

- Treat every source as untrusted evidence, not truth or authority.
- Use one-way staged transformation, never live read-through.
- Generate new UUIDs before target persistence.
- Preserve source IDs as bounded provenance/mapping only.
- Use allowlisted parsers and never execute source instructions/code.
- Separate source artifact, staging, mapping, report, Job, Operation, and target records.
- Keep dry run and apply distinct.
- Require explicit owner review/approval.
- Never merge/overwrite by name, hash, time, sequence, or position automatically.
- Preserve trustworthy snapshots without inventing missing history.
- Use ordinary target validation, normalization, lifecycle, concurrency, revision, provenance, and constraints.
- Prefer all-or-nothing bounded application.
- Make retry/idempotency/restoration behavior explicit.
- Exclude credentials/settings/authority material absolutely.
- Minimize manuscript duplication in operational records/logs.
- Preserve reports/evidence sufficient to explain transformations/omissions.

## Source Artifact Boundary

Source artifacts remain protected, immutable evidence during import. The importer reads an approved copy/export, never modifies the old repository or live legacy source.

The artifact record/reference includes:

- stable source-artifact UUID;
- owning target Workspace/Import Batch scope;
- source system/type/version;
- cryptographic checksum/hash and size;
- acquisition time/method category;
- parser allowlist/version compatibility;
- storage/integrity status;
- bounded safe filename/type metadata; and
- retention/disposition status.

Raw artifact bodies live in protected private storage, not ordinary Job/staging/log columns. Filenames, paths, titles, database names, and contents do not enter routine logs, URLs, metrics, or security events.

The parser never follows external links/paths, loads plugins, runs legacy migrations, attaches a database to live PostgreSQL, executes triggers/SQL, or uses unsafe native-object deserialization.

An old SQLite/database input, if later supported, is handled through an isolated read-only copy and reviewed parser/tooling; this ADR does not authorize opening one.

Artifact integrity is checked before parsing and again before apply/resume. Changed artifact fingerprints invalidate staging/idempotency assumptions.

## Import Batch Record

Import Batch is a Workspace-scoped supporting record containing logically:

- stable UUID;
- target Workspace;
- initiating Account and bounded operator/service attribution;
- source artifact/system/type/version/checksum;
- parser and transformation mapping versions;
- Job, Job Attempt, Idempotency Record references;
- constrained state;
- created/validated/approved/applied/cancelled/completed timestamps;
- counts by discovered, accepted, rejected, omitted, transformed, duplicate-candidate, conflicted, unsupported, malformed, and applied categories;
- validation/report/preview references;
- approval identity/time/scope;
- application Mutation Operation references; and
- bounded error/warning categories.

Batch is not Job: Batch represents import semantics/evidence; Job executes stages. Batch is not Mutation Operation: authoritative application may create one or several operations linked to it. Batch is not authorization.

Likely states include received, validating, staged, needs-review, approved, applying, applied, rejected, cancelled, failed, quarantined, and expired concepts. Exact labels remain later schema work.

Batch reports contain bounded counts, source IDs/types, transformation categories, conflicts, warnings, and omissions. Full manuscript bodies are shown only through authorized preview, not embedded in routine reports/logs.

## Staging Record Boundary

Staging records represent parsed and transformed proposals without domain authority.

Each staged item includes:

- stable UUID;
- Batch/Workspace;
- source entity type/ID/version/fingerprint;
- proposed target type/new UUID;
- source parent/relationship references;
- proposed target parent/order/lifecycle/content-state;
- proposed normalized content reference/hash and representation versions;
- source evidence/reference and transformation warnings;
- duplicate/conflict candidates;
- validation/disposition/review status; and
- mapping/reference to applied result if committed.

Operational staging rows prefer references/hashes/bounded metadata. Large/raw manuscript bodies remain in protected source/staging storage. Authorized previews may render bounded content safely.

Staging is not searchable authoritative content, Scene Revision, Canon, Link, Mutation Operation, or provenance truth. It is excluded from ordinary search/AI context/exports unless a later explicit feature selects it.

Staging may be discarded before apply without domain mutation. After apply, staging can expire while durable target provenance/mapping remains sufficient.

## Identity Mapping

Every imported source entity receives a newly generated target UUID before authoritative application. IDs are never copied from old integer IDs, names, hashes, timestamps, or row order.

Identity Mapping contains:

- stable mapping UUID;
- Batch/Workspace/source artifact;
- source system, namespace/table/type;
- opaque source ID and source version/fingerprint;
- target type and new UUID;
- parent/relationship source and target references as needed;
- transformation version;
- mapping disposition/state;
- applied target existence/reference; and
- timestamps/bounded warnings.

Uniqueness prevents two target identities for the same scoped source identity in one Batch/application and prevents conflicting target reuse. Re-import across Batches may reference earlier mappings but never merges automatically.

Mappings enable relationship reconstruction and duplicate warnings. Possession of source/target IDs or a mapping grants no authorization.

Content equality may help detect duplicate candidates but cannot decide identity. A deliberate duplicate remains a new record with new UUID and provenance.

## Source Validation

Validation is layered and bounded:

1. authorize source upload/selection and target Workspace;
2. verify artifact size, type, checksum, completeness, and allowlisted format/version;
3. reject traversal, symlinks, active content, archive bombs, malformed structures, unsafe serialization, and unsupported encodings;
4. parse with resource/time/depth/count limits;
5. validate source identifiers/types/relationships without trusting them;
6. classify secrets/settings/authority material for exclusion;
7. validate encoding/content/control characters against target policies;
8. inventory unsupported fields/files/references;
9. check mapping uniqueness and cross-Workspace/relationship targets;
10. validate revision/current/lifecycle/order evidence reliability;
11. produce deterministic staged output and bounded report; and
12. recheck artifact fingerprint and mapping version before approval/apply.

Malformed means the artifact cannot be safely interpreted. Unsupported means safely recognized but outside target capability. A warning permits review; a failure blocks the affected Batch/item under explicit policy.

No best-effort parser executes arbitrary content or silently drops semantically important fields. Partial parser errors cannot become partial authoritative writes.

## Legacy Story Engine Classification

Story Engine source data is classified as untrusted imported evidence. It does not define Strange Novelty schema or Canon.

Candidate source families may include old Chapters/current drafts/snapshots, Characters, Locations, and explicit relationship evidence. Other tables are inventoried and deferred until a supported target concept/mapping exists.

Old status fields may conflate workflow, lifecycle, publication, story condition, and authority. They require explicit mapping/warnings; none maps automatically to Canon.

Old settings are excluded wholesale because they mix preferences, provider configuration, style/context material, paths, and secrets. Credentials, provider/model settings, tokens, backup paths, sessions, permissions, and UI/deployment configuration never import.

AI-generated legacy content is not trusted as clean AI Suggestion provenance unless source evidence reliably identifies generation/context. Otherwise it remains Imported content with bounded source note, not automatically authored or Canon.

Old relationships/junction rows are candidate evidence only. Unsupported relationship kinds/endpoints or missing targets are reported. No name-based target linkage is authoritative.

## Scene and Revision Reconstruction

The target Scene model requires a current pointer, initial/current revisions, normalized full content, lineage, revision numbers, lifecycle, order, and provenance.

Version 1 prefers reconstructing trustworthy source snapshots when the source provides identifiable complete content states and sufficient ordering/current evidence.

For each imported Scene candidate:

- allocate one new Scene UUID;
- allocate new Revision UUIDs/numbers in target sequence;
- preserve each trustworthy complete source snapshot as a separate immutable imported Revision;
- normalize each target content value under ADR-0006 and report transformations;
- record source snapshot ID/time/sequence/reliability in provenance;
- create predecessor/base relationships only where supported by evidence;
- select one explicit target current Revision through source-specific rule and owner review;
- create Mutation Operation provenance tied to Batch/mapping; and
- never mutate a reconstructed Revision after commit.

If only current content is trustworthy, import one content Revision (in addition to any implementation-required initial empty Revision handling) and report that history is unavailable. Do not synthesize prior revisions from modification timestamps.

The accepted ordinary Scene creation service creates an initial empty Revision. A bounded import-specific transaction may construct Scene plus imported Revisions/current pointer directly only if it preserves ADR-0004/0008 constraints and provenance. Exact transaction path remains implementation work; redundant empty history should not be hidden.

If the initial empty Revision remains, it is labeled target-creation provenance and imported content follows as later Revision(s). If an import-specific constructor omits it, a later ADR/amendment must prove compatibility with ADR-0008. This ADR prefers using ordinary creation plus imported Revisions for consistency.

## Current-State Selection

Source current state must be explicit and reviewable.

Evidence may include:

- a trustworthy source current-row/current-field semantic;
- explicit current marker;
- documented snapshot/restore relationship;
- validated source sequence designed as current order;
- source application version-specific rules; and
- owner selection during review.

Timestamp recency, highest legacy integer, maximum snapshot number, file order, or UUID/hash does not alone establish current when source semantics are uncertain.

Ambiguous current state blocks automatic apply for that Scene and requires owner choice or import of clearly labeled alternatives/staging. The report explains confidence/evidence without claiming certainty.

Target current pointer and Scene version are newly established under Strange Novelty rules. Source current markers/versions remain provenance and never replace target tokens.

## Lifecycle and Ordering Mapping

Lifecycle mappings are versioned, explicit, and conservative.

- recognized active-like source state may propose active only when semantics are clear and owner approves;
- archived source proposes archived;
- deleted/trashed source proposes trashed or omission according to review;
- unknown/mixed status requires owner classification or blocks the item;
- source publication/Canon/workflow labels do not become lifecycle automatically; and
- purge is never imported as a retained state.

Lifecycle transformation records source value, mapping rule/version, target proposal, warning, and owner disposition.

Ordering transformations use source parent/group/position evidence to generate deterministic target sparse order. Collisions, missing/duplicate positions, non-numeric values, gaps, and ambiguous parent groups are reported.

Title, creation time, UUID, or database row order are not fallback identity/order authority. A deterministic staging fallback may sort by bounded source identity solely for repeatable preview, clearly labeled as reconstructed order requiring review.

Target order changes do not rewrite imported Revision content.

## Provenance and Mutation Operations

Applied imported records retain enough provenance to explain source and transformation without embedding full source bodies unnecessarily.

Provenance includes:

- Import Batch and Identity Mapping IDs;
- source artifact/system/type/version/checksum;
- source entity/snapshot identifiers;
- parser/transformation/mapping versions;
- source/current/order/lifecycle evidence and warnings;
- normalization changes and target representation versions;
- owner review/approval and application time;
- target UUIDs/Revision relationships;
- omitted/unsupported relationship evidence where relevant; and
- Mutation Operation IDs.

Each authoritative target mutation uses an Import Apply source category and ordinary Mutation Operation. Provenance does not make content Canon, approved beyond the specific apply action, or authorized for future operations.

Import Batch is not Mutation Operation; one Batch may produce multiple target operations inside an atomic application plan. Mutation Operation remains immutable evidence after staging cleanup.

Security events record import initiation/approval/application/failure categories without manuscript/source payloads. They remain separate.

## Duplicate and Conflict Handling

Duplicate detection compares bounded evidence such as:

- prior source-system/type/ID mappings;
- exact source artifact/entity fingerprints;
- target titles/aliases;
- exact normalized content hashes;
- similar text/metadata;
- parent/order/relationship context; and
- source timestamps.

These yield candidates/warnings, not merge/overwrite authority.

Version 1 behavior:

- same Batch/source identity/fingerprint converges through idempotency/mapping;
- same identity with changed fingerprint fails/requires explicit new Batch/version handling;
- prior Batch mapping is surfaced for review;
- title/hash/similarity matches never auto-merge;
- existing target Scenes are not overwritten;
- revision chains are not spliced automatically;
- relationship endpoint conflicts are reported; and
- owner may skip, create duplicate, or choose a later explicitly supported merge/copy workflow.

Applying imported content to an existing Scene is a different explicit domain operation requiring current Scene token, review, and conflict handling. It is not the default import path.

## Dry Run and Preview

Every Version 1 import performs a dry run before authoritative apply.

Dry run produces:

- verified artifact/source/parser versions;
- proposed target Workspace and counts;
- identity mapping plan;
- record/type classification;
- Scene/revision/current-history plan;
- lifecycle/order transformations;
- duplicate/conflict candidates;
- missing relationships;
- normalization transformations;
- unsupported/omitted fields/attachments/references;
- secret/authority exclusions;
- warnings/failures;
- estimated transaction/resource bounds; and
- deterministic report/preview integrity hash.

Preview is authorized and safely renders bounded source/proposed content comparisons. Full source manuscripts are not copied into logs/reports unnecessarily.

Dry-run success does not reserve target state forever. Apply revalidates Workspace, mappings, artifact/report hash, approval, target conflicts, and transaction limits.

The same input/parser/transformation/version should produce equivalent staging/mapping plans, subject to explicitly recorded target-state duplicate checks.

## Human Review and Approval

The authorized owner reviews Batch-level summary and item-level warnings/conflicts before apply.

Review distinguishes:

- accept proposed new record/history;
- reject/skip;
- retain unsupported evidence for later;
- classify unknown lifecycle/current state;
- resolve ordering/parent ambiguity;
- acknowledge transformation/loss warnings;
- choose among duplicate candidates without automatic merge; and
- cancel the Batch.

Approval is scoped to a specific Batch, source artifact fingerprint, transformation/mapping version, target Workspace, mapping plan/report hash, and item dispositions. Changed artifact or mapping invalidates approval.

Approval is not execution, Canon, broad source ownership proof, future import permission, or authorization to overwrite existing data.

Workers/operators cannot approve. Staff/superuser/database-admin status does not imply creative import approval. High-impact application may require recent authentication under later policy.

## Import Application

Application occurs only after successful dry run and explicit approval.

Django revalidates:

- current Account/session/Grant and target Workspace;
- Batch state/approval/report hash;
- source artifact checksum/availability;
- parser/transformation/mapping versions;
- source-to-target mapping uniqueness;
- target UUID nonexistence and no cross-Workspace conflicts;
- target lifecycle/order/current/history plan;
- normalization/content limits;
- relationship target availability;
- idempotency/application status; and
- transaction-size/resource bounds.

The apply service creates target records through explicit domain services/constraints. Scene import creates Scene, immutable Revisions, current pointer/version, lifecycle/order, Mutation Operations, and source mappings as one approved plan.

Applied imported content becomes ordinary authoritative Strange Novelty data with Imported state/provenance. Later edits, links, state changes, search indexing, exports, backup, and restoration use normal rules.

No source table maps directly one-for-one by convenience. Unsupported domain concepts remain staging/evidence, not generic target blobs masquerading as authority.

## Transaction and Atomicity Boundary

Version 1 prefers one bounded all-or-nothing PostgreSQL application transaction per approved Import Batch.

The transaction:

1. locks/checks Batch/idempotency/application state;
2. validates target Workspace/approval/mappings;
3. creates Mutation Operations;
4. creates target aggregate records and immutable Revisions;
5. creates target relationships only when all endpoints/invariants are valid;
6. advances current pointers/versions according to import plan;
7. finalizes mappings/applied references/counts;
8. dispatches commit-coupled search/derived Jobs; and
9. commits everything or rolls back everything.

Parsing/provider/file I/O and long transformation work occur before the transaction. No source artifact read or external call holds database locks.

If representative Batch size exceeds safe transaction duration/locks, Version 1 does not silently become best-effort. A later decision must define durable checkpoints, visibility, compensation, resume identity, partial-Batch semantics, and rollback.

All-or-nothing applies to the approved Batch scope, not unrelated Workspace records.

## Idempotency, Retry, Cancellation, and Resumability

Import uses ADR-0010 with Batch-level Idempotency Record scoped to Workspace, source artifact fingerprint, parser/transformation version, mapping plan/report hash, and operation key.

- duplicate Job delivery converges on existing Batch/staging/apply result;
- source identity mappings are unique;
- same key/same fingerprint returns/reconciles prior state;
- same key/changed fingerprint/version/report fails;
- retries revalidate source/authorization/Batch state;
- parsing/indexing transient failures retry within budgets;
- malformed/authorization/mapping-conflict failures are terminal or review-required;
- ambiguous application commit is reconciled through Batch/idempotency/mappings before retry; and
- attempts retain bounded evidence without source bodies.

Cancellation before apply can stop Jobs and mark/discard staging under retention policy. During the short apply transaction, cancellation is cooperative before start or safe checkpoints; commit is atomic. After commit, cancellation does not undo target data.

Resumability is claimed only for durable staged phases with stable artifact/mapping/version checks. Application itself is retried/reconciled atomically, not resumed item-by-item.

Starting a new import of changed source is a new Batch, not a retry.

## Failure and Rollback

Failures include corrupt/incomplete artifact, unsupported source version, unsafe format, malformed encoding, secret detection, oversized/deep input, mapping collision, missing required target, ambiguous current/history, invalid lifecycle/order, cross-Workspace reference, changed fingerprint, stale approval, transaction conflict, and storage/worker failure.

Failure behavior:

- no authoritative writes during parse/dry run;
- apply validation failure creates no target mutation;
- atomic apply failure rolls back all Batch target writes;
- incomplete artifacts/reports are never approved/applied;
- failures report bounded categories/items, not full source text/path/SQL;
- original source evidence remains unchanged; and
- unrelated target data is never deleted/repaired automatically.

Before apply, “rollback” means discard staging/approval while retaining bounded evidence under policy. After apply, reversal is a separately authorized dependency-aware operation. It must identify exactly imported target records, protect later edits/links/revisions, avoid unrelated data, and preserve immutable provenance.

Restoring a pre-import backup is disaster recovery, not ordinary import rollback, and can discard unrelated later work. It is not the default reversal.

No automatic best-effort repair fabricates mappings/history or silently drops invalid records.

## Attachments, Paths, and External References

Until attachment support is accepted, encountered files/paths/URLs are inventoried and reported, not imported into authoritative storage.

The importer must reject or safely handle:

- absolute/relative traversal paths;
- symlinks/hard links/device files;
- archive bombs/nested archives;
- executable files/scripts/macros/plugins;
- active HTML/SVG/documents;
- unsafe filenames/control characters;
- oversized/unsupported media;
- remote URLs/redirects/internal addresses; and
- missing or changed referenced files.

No path/URL is followed automatically. No server-side fetch occurs. Future attachment import requires a separate media/object-storage/parser decision with type/size/malware/rights/provenance/export/backup rules.

Source paths and filenames are private metadata and do not enter routine logs/object keys. Bounded safe display may be shown in authorized inventory.

Embedded source code, SQL, templates, migration instructions, prompts, and scripts remain inert data and are never executed.

## Authorization and Workspace Scoping

Authorization occurs at source upload/selection, Batch creation, validation/preview, item review, approval, application, report/artifact access, cancellation, reversal, retention cleanup, and restored-Batch reconciliation.

Every Batch, staged item, mapping, report, Job, artifact, operation, and target reference carries/directly resolves one target Workspace. Cross-Workspace source relationships cannot create target cross-Workspace links; they fail or require explicit remapping within the selected Workspace.

Enqueue-time authorization is insufficient. Workers re-resolve current Account/service authority, Grant, target Workspace, artifact/mapping access, Batch state, and operation limits before each meaningful phase.

Source IDs, checksums, mapping IDs, Batch IDs, paths, titles, owner claims, and possession of an artifact grant no target authority.

Import into a new Workspace still requires explicit creation/Grant authorization. Source Account/grant/permission records are never applied.

## Privacy, Secrets, and Logging

Source artifacts may contain complete manuscripts, personal data, paths, credentials, provider settings, logs, or deleted history. They receive private-archive protection.

Secrets/authority material are excluded and never copied into staging/provenance/reports:

- passwords/hashes where not explicitly required as inert source evidence;
- API keys/tokens/provider credentials;
- cookies/sessions/reset links;
- MFA/TOTP/recovery material;
- encryption/signing/private keys;
- database/deployment credentials;
- environment configuration;
- source grants/roles/permissions; and
- secret-bearing settings/backups.

Routine logs/metrics/security events contain Batch/Job type/state, counts, duration, size buckets, parser/transformation version, safe warning/error categories, and non-secret correlation IDs.

They exclude manuscript text, raw payloads, titles, filenames/paths, source IDs where unnecessary, queries, credentials, stack locals, SQL, and full reports.

Previews/reports are authorized private content, escaped/safely rendered, bounded, and protected from caching/download leakage. Import parsing uses denial-of-service limits and isolated processing where appropriate.

## Restore and Recovery Reconciliation

Same-archive restoration preserves applied target UUIDs, Revisions, Mutation Operations, Import Batch/mapping provenance included by policy, and target current state. It does not rerun import.

After database/archive restoration:

- unfinished Import Jobs/Attempts/leases are quarantined;
- staged/applying Batches are not resumed blindly;
- source artifact availability/checksum and mapping/report versions are revalidated;
- ambiguous apply outcome is reconciled through target UUIDs/mappings/idempotency;
- applied Batches remain applied if target records/invariants verify;
- Jobs safe to rerun (validation/report) may be regenerated after authorization;
- owner approval may require renewal if target/source/recovery state changed;
- search/derived projections rebuild from applied authoritative targets; and
- source secrets/settings remain excluded/inactive.

Cross-Workspace import after restore still assigns new IDs. Restored mappings do not authorize merge/re-import.

Structured archives may include bounded Import Batch/mapping/provenance needed to explain applied records. Raw source artifacts/staging are included only under explicit retention/archive policy and remain untrusted.

Point-in-time recovery can restore Batch state before/after apply inconsistently with external artifact storage; reconciliation verifies both before action.

## Retention and Cleanup

Retention categories include:

- source artifact;
- parsed/raw staging content;
- normalized proposals/previews;
- validation/import reports;
- identity mappings;
- Batch/Job/Attempt/Idempotency evidence;
- applied Mutation Operations/provenance; and
- security events.

Raw artifacts/staging are retained only as long as needed for review, retry, reconciliation, recovery, and owner-controlled evidence. Exact durations are later policy.

Applied identity mappings and bounded provenance may need longer retention to explain origin, prevent duplicate re-import, and support export/restoration. They should not retain full manuscripts where hashes/references suffice.

Cleanup is authorized, Workspace-scoped, idempotent, and protective. Deleting source artifact/staging/Batch operational detail cannot cascade to applied Scene, Revision, Link, Mutation Operation, lifecycle, search projection authority, export, or backup.

Rejected/expired Batches are cleaned under privacy policy while preserving minimal evidence needed to explain deletion/idempotency/security. Backups may retain artifacts/staging until expiry under ADR-0009.

## Django Application Boundary

Django services own source registration, parser selection, limits, validation, staging, mapping, duplicate/conflict detection, preview, approval, idempotency, Jobs, application transactions, provenance, reversal, retention, and privacy-safe errors.

Parsers return typed provider/source-neutral intermediate records. They never write domain tables directly. Source-specific mapping remains behind an adapter/version boundary.

Workers call the same scoped services and cannot approve/apply around owner authorization. Application uses ordinary aggregate/revision/link/lifecycle services rather than bulk SQL bypass.

Django serialization/fixtures are not automatically safe import formats. Language-native deserialization and arbitrary model loading are rejected.

No code, models, migrations, parsers, commands, Jobs, APIs, or tests are created by this ADR.

## PostgreSQL Boundary

PostgreSQL will eventually store Import Batch, staged-item metadata/references, Identity Mapping, reports/operations references, and applied target records.

Constraints should reinforce:

- UUID uniqueness;
- direct Workspace consistency;
- unique scoped source identity/fingerprint mapping;
- unique target assignment within Batch;
- valid Batch/item/mapping states;
- protective applied-target/provenance references;
- no cross-Workspace mapping/application;
- report/approval/application consistency where row-local; and
- no cascades from staging cleanup to authoritative targets.

PostgreSQL transactions provide all-or-nothing bounded apply. Parsing/large artifact processing occurs outside database transactions.

Database constraints cannot decide source truth, duplicate identity, current-history reliability, Canon, owner approval, or safe parser behavior. Django services/human review do.

No foreign data wrapper, attached legacy database, SQL import, unsafe copy, database connection, or schema object is created/selected here.

## Rationale

Staging separates hostile/incomplete evidence from authoritative data and gives the owner a reviewable mapping before irreversible relationships/history are created.

New UUIDs prevent legacy database-local integers, names, hashes, and source permissions from colliding with target identity. Durable mappings preserve provenance and relationship transformation without granting authority.

Trustworthy snapshot reconstruction preserves useful recovery history while refusing to invent chronology that the source cannot prove. Ordinary target revisions/lifecycle/order make imported records immediately compatible with export, backup, search, and restoration.

Bounded all-or-nothing apply avoids Story Engine's item-by-item partial success and simplifies rollback/idempotency for the initial one-owner workload.

Allowlisted parsers, secret exclusion, inert paths/attachments, and privacy-safe records reduce the high-risk input surface. Restore quarantine prevents recovery from duplicating imports.

## Decision Criteria

Options are evaluated against:

1. target stable identity and Workspace isolation;
2. no inherited authority/Canon/credentials;
3. exact source evidence and explicit transformation provenance;
4. immutable revision/current-pointer/lifecycle/order integrity;
5. human review and no silent merge/overwrite;
6. hostile-input/parser safety;
7. atomicity/idempotency/recovery behavior;
8. privacy/log/retention minimization;
9. explainable omission/unsupported/conflict reporting;
10. future source-format portability;
11. maintainability for one bounded Version 1 importer;
12. export/backup/restoration compatibility; and
13. no dependency on the old application/runtime.

## Alternatives Considered

### No legacy import

Safest/simplest, but loses practical migration path and forces manual work. Not selected as permanent policy; unsupported source families may still remain unimportable.

### Manual copy and paste

Useful fallback for a few Scenes and preserves owner control, but loses structured provenance/history/mappings and is error-prone at scale.

### Direct database reuse

Rejected because old identity/schema/security/state/revision semantics conflict and live coupling prevents clean migration.

### Ongoing read-through of legacy data

Rejected. It makes the old repository/database an operational dependency/source of truth and complicates privacy/recovery.

### One-way staged import

Selected.

### Preserve legacy IDs as target IDs

Rejected. Integers are source-local/non-portable and may collide or imply authority.

### Assign new UUIDs with mappings

Selected.

### Merge by title

Rejected because titles change/collide and are not identity.

### Merge by content hash

Rejected because equality is not identity and revisions/contexts may legitimately duplicate content.

### Never merge automatically

Selected. Owner chooses skip/duplicate/future explicit merge.

### One current revision only

Acceptable fallback when no trustworthy source history exists; report lost/unavailable history.

### Reconstruct trustworthy source snapshots

Selected where complete states/order/current evidence are reliable.

### Fabricate history from timestamps

Rejected.

### Import into existing Workspace

Allowed only with explicit staging/duplicate/conflict review; higher risk.

### Import into new Workspace

Preferred for isolation when appropriate, but not mandatory if owner deliberately targets an existing Workspace.

### One large transaction

Selected for bounded Version 1 apply after resource validation.

### Checkpointed multi-transaction apply

Deferred until size evidence and explicit resumability/compensation design justify it.

### Best-effort partial import

Rejected because partial relationships/history and unclear rollback undermine trust.

### All-or-nothing import

Selected for approved bounded Batch.

### Direct authoritative writes while parsing

Rejected.

### Staging and approval before apply

Selected.

### Unsafe native-object deserialization

Rejected.

### Allowlisted versioned parsers

Selected.

### Retain full raw source indefinitely

Rejected due to manuscript/secret duplication and privacy.

### Bounded source retention

Selected.

### Include credentials/settings

Rejected absolutely.

### Exclude all secrets and authority material

Selected.

### Automatic path or URL following

Rejected due to SSRF/traversal/external changes and attachment scope.

### Inventory external references only

Selected until attachment/import support exists.

### Automatic duplicate merge

Rejected.

### Warnings and explicit owner decisions

Selected.

### Resume all restored imports

Rejected.

### Quarantine restored imports

Selected.

## Comparative Assessment

### Import strategy

| Strategy | Authority safety | Provenance | Operations | Decision |
| --- | --- | --- | --- | --- |
| Manual copy | Strong human control | Weak | Manual | Fallback |
| Direct DB reuse | Poor | Ambiguous | Coupled | Rejected |
| Live read-through | Poor | External dependency | High | Rejected |
| Staged one-way import | Strong | Strong | Moderate | Selected |

### Identity strategy

| Strategy | Collision/portability | Relationship mapping | Decision |
| --- | --- | --- | --- |
| Legacy IDs target IDs | Weak | Direct but unsafe | Rejected |
| Titles/hashes identity | Weak/ambiguous | Unreliable | Rejected |
| New UUIDs + mappings | Strong | Explicit | Selected |

### Revision-history strategy

| Strategy | Fidelity | Fabrication risk | Decision |
| --- | --- | --- | --- |
| Current only always | Loses snapshots | Low | Fallback only |
| Trustworthy snapshots | Strong where evidenced | Controlled | Selected |
| Timestamp-fabricated chain | Misleading | High | Rejected |
| Import every row as revision | No semantic filter | High | Rejected |

### Target Workspace strategy

| Target | Isolation | Conflict risk | Decision |
| --- | --- | --- | --- |
| New Workspace | Strongest | Lowest | Preferred |
| Explicit existing Workspace | Moderate | Higher/reviewed | Allowed staged |
| Implicit current Workspace | Weak | High | Rejected |

### Duplicate handling

| Strategy | Data-loss risk | Owner effort | Decision |
| --- | --- | --- | --- |
| Auto title merge | High | Low | Rejected |
| Auto hash merge | High | Low | Rejected |
| Always duplicate silently | Low overwrite; clutter | Low | Rejected silent behavior |
| Warn + explicit choice | Lowest | Higher | Selected |

### Atomicity and partial failure

| Strategy | Consistency | Scalability | Decision |
| --- | --- | --- | --- |
| Item-by-item best effort | Weak | High | Rejected V1 |
| One bounded transaction | Strong | Limited size | Selected |
| Durable checkpoint workflow | Strong if designed | High | Deferred |
| Direct parse-and-write | Weak | Moderate | Rejected |

### Parser and source safety

| Strategy | Compatibility | Security | Decision |
| --- | --- | --- | --- |
| Native object deserialize | Broad/easy | Poor | Rejected |
| Execute legacy code/migrations | High source fidelity | Very poor | Rejected |
| Allowlisted versioned parser | Bounded | Strong | Selected |
| Follow paths/URLs | More data | SSRF/traversal | Rejected |

### Retention strategy

| Strategy | Troubleshooting/provenance | Privacy/storage | Decision |
| --- | --- | --- | --- |
| Delete immediately | Weak | Strong | Insufficient |
| Retain raw indefinitely | Strong | Poor | Rejected |
| Bounded category retention | Strong enough | Controlled | Selected |

### Restore-time behavior

| Strategy | Duplicate risk | Recovery effort | Decision |
| --- | --- | --- | --- |
| Resume all | High | Low initially | Rejected |
| Cancel/delete all evidence | Lost reconciliation | Moderate | Rejected |
| Quarantine/reconcile | Controlled | Higher | Selected |
| Re-run as new import silently | Duplicate identities | High | Rejected |

## Evidence

### Repository evidence

- Product vision/principles require imported content remain distinguishable and never become Canon automatically.
- Scope/roadmap defer broad migration while requiring secure ownership, provenance, export, backup, and restoration foundations.
- Data model defines staged Import Batch/items, explicit Workspace identity, provenance, source mappings, and Imported state.
- Security architecture treats uploads/databases/archives/documents as hostile and requires limits, isolation, safe logs, and server authorization.
- Integration architecture defines inbound import as staged/untrusted and rejects provider identity/authority.
- ADR-0001 through ADR-0012 establish Django/PostgreSQL, UUIDs, immutable revisions, content normalization, Workspace schema, archive/restoration identity rules, Jobs/idempotency, AI staging, and rebuildable search.
- Architecture handoff identifies import/legacy migration as a later ADR after core/recovery/job boundaries.
- Story Engine audit explicitly documents incompatible integer IDs, missing Workspace/provenance, direct writes, name matching, partial imports, mixed credentials/settings, and candidate source families.

### Official guidance reviewed conceptually

- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [Django file uploads](https://docs.djangoproject.com/en/stable/topics/http/file-uploads/)
- [Django validation](https://docs.djangoproject.com/en/stable/ref/validators/)
- [Django serialization](https://docs.djangoproject.com/en/stable/topics/serialization/)
- [Django security](https://docs.djangoproject.com/en/stable/topics/security/)
- [PostgreSQL transactions/isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [OWASP Deserialization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html)
- [OWASP Path Traversal guidance](https://owasp.org/www-community/attacks/Path_Traversal)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
- [OWASP Denial of Service Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP Error Handling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Error_Handling_Cheat_Sheet.html)

This supports bounded uploads, untrusted parsing, no unsafe deserialization, authorization at every phase, transactions/constraints, path/SSRF protection, secret exclusion, DoS limits, and safe logs/errors.

### Evidence still required

Before implementation:

- define supported source artifact types/Story Engine versions without accessing private data;
- create source schema/mapping specifications from approved synthetic fixtures/audit evidence;
- define parser isolation/limits and artifact storage;
- define Batch/staged item/mapping/report physical schemas;
- define source/current/snapshot reliability rules by supported version;
- define target initial-empty/imported-revision transaction path;
- define lifecycle/order/status mapping tables and warnings;
- define duplicate candidate algorithms and owner review UX;
- set Batch size/transaction limits and prove bounded all-or-nothing feasibility;
- define checkpointed alternative only if evidence requires it;
- define attachment/reference inventory and omission behavior;
- define retention/cleanup/archive inclusion;
- test idempotency/cancellation/restore quarantine;
- test hostile/malformed/oversized/path/archive/deserialization inputs; and
- use synthetic source artifacts only until explicit private-data access is authorized.

## Consequences

### Positive

- Legacy/source identity cannot corrupt target UUID identity.
- Staging prevents hostile/incomplete data from reaching authority.
- Owner sees transformations, omissions, duplicates, and history evidence before apply.
- Trustworthy snapshots preserve useful history without fabrication.
- All-or-nothing bounded apply avoids unexplained partial migrations.
- Source mappings preserve provenance and relationships.
- Secrets/settings/permissions cannot become target authority.
- Ordinary target records immediately follow revision/lifecycle/search/backup rules.
- Restore quarantine prevents duplicate application.
- Source formats can evolve behind versioned adapters.

### Negative

- Mapping/staging/report/provenance schemas and UX are substantial work.
- New UUIDs require every relationship/reference to be remapped.
- Conservative rules may omit unsupported legacy data.
- Owner review can be lengthy for many conflicts/unknown states.
- All-or-nothing transaction limits Batch size.
- Trustworthiness evaluation of old snapshots/current state may be uncertain.
- Keeping source evidence/staging adds sensitive duplicate storage.
- Reversal after apply is difficult once later target edits exist.
- New Workspace preference may fragment content until deliberate organization.
- No automatic merge means more duplicates/manual decisions.

### Neutral or Operational

- Exact source versions/parsers remain later work.
- Manual copy remains fallback.
- Attachment import waits for media architecture.
- Legacy AI-origin classification may remain unknown.
- Imported content can later be reviewed/reclassified through ordinary actions.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Legacy ID reused as target | Collision/authority corruption | New UUIDs and mapping constraints | Mapping bugs remain |
| Merge by title/hash | Silent overwrite/identity collapse | Warnings only; explicit owner choice | Owner may choose wrong candidate |
| Source secrets imported | Credential compromise | Absolute exclusions, scanners/allowlists, tests | Unknown secret-like fields may evade detection |
| Parser executes source | Code/system compromise | Allowlisted parsers, no native deserialization/code/SQL | Parser vulnerabilities remain |
| Archive/path traversal | File disclosure/write | No automatic path following, normalization/isolation/limits | Future attachment support adds risk |
| Archive bomb/oversize | DoS | size/depth/count/time/memory limits | Resource exhaustion still possible |
| History fabricated | Misleading provenance | Trust criteria/warnings/owner current selection | Source evidence may remain ambiguous |
| Wrong current snapshot | Wrong manuscript state | Explicit source rules and review, no timestamp-only inference | Human error remains |
| Normalization silently changes text | Creative corruption | Transformation report, source evidence, hashes | Unicode edge cases remain |
| Partial import commits | Broken relationships/history | One bounded transaction | Large batches may not fit |
| Retry duplicates records | Clutter/integrity failure | Batch idempotency + unique mappings/target UUIDs | Changed source needs explicit new Batch |
| Existing Workspace conflict | Overwrite/cross-links | No overwrite/merge, staged candidates | Review burden high |
| Unknown lifecycle becomes active | Privacy/workflow error | Conservative mapping/owner classification | Source semantics may be undocumented |
| Missing relationship silently dropped | Lost meaning | Semantically important missing target warning/failure | Some omissions may be unavoidable |
| Staging leaks manuscripts | Privacy breach | protected storage, bounded retention, references/hashes/log exclusions | Extra copies increase exposure |
| Applied import reversal deletes later edits | Data loss | Separate dependency-aware reversal; protect later records | Reversal may be impossible cleanly |
| Restore resumes import | Duplicate apply | quarantine/reconcile mappings/idempotency | Manual recovery cost |
| Report/log leaks titles/paths | Privacy breach | bounded reports, safe logs/filenames, access controls | Authorized previews necessarily reveal content |
| Old repository modified | Evidence loss | reference-only invariant; use approved copies/exports | Operator error outside app remains |
| Generic metadata becomes data dump | Schema/privacy debt | bounded versioned fields and omission reports | Future unsupported fields pressure expansion |

## Security and Privacy Review

- Security-sensitive: Yes; import processes untrusted artifacts that may contain complete manuscripts, credentials, code, and hostile structures.
- Primary references: `docs/architecture/security.md`, `docs/architecture/data-model.md`, ADR-0001 through ADR-0012.
- Additional references: product docs, integrations, architecture handoff, and Story Engine audit.

### Assets and trust boundaries

Assets include target Workspace, source artifacts, staging/manuscripts, mappings, reports, Jobs, credentials, applied records, provenance, and backups. Browser upload/preview, artifact storage, parser worker, source formats, and legacy references cross trust boundaries.

### Authorization and authority

Django authenticates/authorizes every stage. Source IDs, owner fields, grants, permissions, credentials, statuses, and Canon labels never authorize target actions. Workers/operators cannot approve.

### Parser and file safety

Parsers are allowlisted/versioned/resource-bounded. Unsafe deserialization, code/SQL/shell/templates/macros/plugins, path following, network fetching, active content, and archive traversal are prohibited. Future files require separate scanning/object rules.

### Privacy and logging

Artifacts/staging/reports are private. Logs/metrics/events exclude text/titles/paths/raw payloads/secrets. Previews escape content and use protected responses/caching/download policies.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- every import phase authorization/Workspace scope/recent-auth where required;
- changed artifact/report/mapping invalidating approval;
- new UUID/mapping uniqueness and cross-Workspace rejection;
- title/hash/timestamp matches never auto-merging;
- source snapshot/current/lifecycle/order reliability/warnings;
- exact source evidence and target normalization transformation reporting;
- all-or-nothing application/rollback at every failure point;
- Job duplicate/retry/cancellation/ambiguous commit/idempotency;
- malformed encodings, null/control/bidi/Unicode limits;
- archive bombs, traversal, symlinks, device/executable/active files;
- unsafe native serialization/code/SQL/template/macro/plugin rejection;
- URL/SSRF no-follow behavior;
- secret/settings/session/MFA/provider/deployment exclusion;
- missing relationship/unsupported attachment inventory;
- safe preview/report/log/error/metric behavior;
- staging cleanup without authoritative cascade;
- structured archive/backup provenance and restore quarantine; and
- proof no test touches/modifies old repository or private databases.

### Residual risk

Parsing complex legacy formats can expose vulnerabilities and consume resources. Source semantics may be undocumented, so history/current/lifecycle mapping can remain uncertain. Authorized operators see private source content. New IDs/mappings can be wrong despite validation. Bounded retention creates extra sensitive copies. All-or-nothing imports can be slow or fail for large sources.

## Product and Architecture Alignment

### Product alignment

The decision enforces “import without assuming authority,” preserves author control, privacy, provenance, stable identity, recovery, and explicit content-state distinctions.

### Scope alignment

It defines a safe migration boundary without moving automatic full Story Engine migration into Version 1. Only supported record families/formats may be implemented later.

### ADR alignment

- ADR-0001: browser/source remain untrusted; Django mediates.
- ADR-0002: import stays in modular-monolith services/adapters.
- ADR-0003: PostgreSQL constraints/transactions protect target state.
- ADR-0004: new UUIDs, mapping provenance, immutable revisions, no overwrite/merge.
- ADR-0005: source accounts/grants/secrets confer no target authority.
- ADR-0006: target Scene content follows normalized plain-text rules.
- ADR-0007: Import Batch/mappings/supporting records remain separate.
- ADR-0008: target UUID/current/lifecycle/order/provenance constraints hold.
- ADR-0009: import differs from same-archive restoration/new identity behavior.
- ADR-0010: Jobs/idempotency/cancellation/recovery quarantine apply.
- ADR-0011: legacy/provider output does not inherit AI authority/approval.
- ADR-0012: applied target data gets new rebuildable projections; staging is not search authority.

### Architecture alignment

The model implements staged untrusted input, stable mappings, explicit review, no source authority, bounded Jobs, safe recovery, private logs, and provider-independent portability.

### Normative-document impact

If accepted, data-model, security, integration, backup/restoration, jobs, search, and roadmap docs should be reconciled with Batch/staging/mapping, all-or-nothing apply, trustworthy snapshot reconstruction, secret exclusion, and restore quarantine. The ADR index should be updated. No implementation is authorized.

## Migration and Portability

Source adapters/versioned mappings convert supported formats to a provider-neutral staged model. Target domain semantics remain independent of Story Engine tables/code/runtime.

New UUIDs and explicit mappings allow multiple source systems and provider changes without source key collision. Source namespaces/types/versions/checksums remain portable provenance metadata.

Applied target records export/restore normally. Structured archives may preserve bounded Batch/mapping/provenance; same-archive restoration preserves target IDs. Cross-Workspace re-import creates new target IDs unless a future explicit merge/clone decision says otherwise.

Parser/transformation upgrades create new dry runs/Batches or explicit compatible staging migrations; they do not silently reinterpret applied records. Original source evidence is unchanged.

The old repository remains reference-only and never becomes an operational dependency.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Select bounded supported source formats/Story Engine versions from audit/synthetic evidence only.
- [ ] Define source artifact, Batch, staged item, mapping, report, and provenance schemas.
- [ ] Define allowlisted parser interface, isolation, limits, versioning, and safe errors.
- [ ] Define source record-family mappings and unsupported-field inventory.
- [ ] Define trustworthy snapshot/current-state criteria and owner review UX.
- [ ] Define target initial-empty/imported-revision construction transaction.
- [ ] Define lifecycle/order/content-state transformation rules and warnings.
- [ ] Define duplicate-candidate algorithms without merge authority.
- [ ] Define report/preview integrity hashes and approval binding.
- [ ] Measure synthetic Batch sizes and confirm one-transaction apply bounds.
- [ ] Draft checkpoint/compensation ADR only if bounded transaction is insufficient.
- [ ] Define source/staging/report/mapping retention and structured archive inclusion.
- [ ] Define attachment/reference inventory until media architecture exists.
- [ ] Define reversal safeguards for later-edited imported records.
- [ ] Define restore-time Batch/Job/mapping reconciliation.
- [ ] Add later parser/security/authorization/mapping/revision/atomicity/idempotency/restore tests using synthetic artifacts.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes code, Django initialization, models, migrations, database objects, SQL, import scripts, commands, Jobs, parsers, schemas, tests, packages, fixtures, sample imports, source/database connections, legacy code execution/deserialization, deployment, access/modification of `/home/burmuss/projects/the-story-engine`, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No application code, model, migration, database object, SQL, import script, command, Job, parser, schema, test, package, fixture, sample import, source/database connection, legacy execution, deployment configuration, supported source version, mapping, limit, retention duration, or transaction size is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
