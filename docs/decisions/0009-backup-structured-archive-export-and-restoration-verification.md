# ADR-0009: Backup, Structured Archive Export, and Restoration Verification

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes the Version 1 boundaries for database backup, human-readable export, structured portable archive export, same-archive restoration, cross-Workspace import, restoration verification and activation, retention, encryption, integrity manifests, recovery testing, failure behavior, and administrative authority, while exact PostgreSQL and Django versions, deployment, provider, object store, backup mechanism, archive container and serialization, compression, encryption and hashing algorithms, optional signature model, key custody, retention durations, RPO, RTO, schedules, storage locations, restore-test frequency, job system, and operational commands remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; PostgreSQL, Django, security, privacy, authorization, backup, archive, migration, restoration, incident-response, and operational perspectives

## Context

Strange Novelty holds a private creative archive whose value depends not only on current manuscript text but also on stable identity, immutable revisions, lineage, ordering, lifecycle, provenance, Workspace scope, grants, and recoverable history. A readable copy protects author access to prose; it does not reconstruct the application. A database backup supports disaster recovery; it is not a portable application contract. A structured archive can preserve application semantics across deployments; it is not automatically a trusted backup or an import into another Workspace.

ADR-0001 through ADR-0008 establish the trust boundary and the authoritative schema direction. The browser is untrusted. Django application/query services authorize every private operation. PostgreSQL is authoritative for structured relational state. Stable UUIDs identify Account, Workspace, Workspace Grant, Mutation Operation, Scene, and Scene Revision. Every committed Scene has an initial empty revision. Scene Revision stores immutable complete normalized UTF-8 content. Scene current pointer/version, revision numbers, lineage, lifecycle, sparse order, provenance, and same-Workspace constraints must survive recovery exactly.

Protective deletion retains authoritative history. Supporting records grant no authority by reference. Administrative capability is not creative approval. Manuscript content and credentials must not leak through logs, filenames, URLs, metrics, security events, or provenance.

The old Story Engine demonstrates why naming an export a recovery format or copying a live database is insufficient: its structured export was incomplete, backups lacked integrity evidence, provider credentials could be co-located, and no representative restoration verification existed. Strange Novelty must define recoverability before implementation.

The decision must distinguish:

- backup from export;
- human-readable export from structured archive;
- structured archive from import;
- import from restoration;
- restoration from migration;
- migration from repair;
- repair from author edit;
- same-archive restoration from cross-Workspace import;
- database backup from application-level archive;
- backup retention from application lifecycle;
- purge from backup expiry;
- trash from deletion;
- exact content preservation from content normalization;
- archive-format version from schema migration version;
- content-format version from normalization version;
- cryptographic integrity from authenticity;
- checksums from digital signatures;
- encrypted storage from authorized restoration;
- technical restore execution from owner approval;
- restore verification from restore activation;
- operator access from creative authority;
- source Account identity from target Account authorization;
- current pointer from revision order;
- stable-ID preservation from identity mapping;
- partial data load from complete valid restoration;
- failure rollback from destructive recovery;
- restore staging from production activation;
- disaster recovery from routine export;
- backup success from verified recoverability; and
- retention policy from implementation mechanism.

Exact PostgreSQL/Django versions, deployment, provider, object store, backup vendor, archive container, compression, encryption algorithm, signing mechanism, retention durations, RPO, RTO, storage location, region, and command line remain undecided.

## Decision

If accepted, Version 1 will use the following recovery model.

1. Produce and name three distinct artifact classes: human-readable author export, structured portable archive, and PostgreSQL database backup.
2. Human-readable export is for reading and external use. It is non-authoritative and not sufficient for exact restoration.
3. Structured archive is a full-Workspace application-level package that preserves authoritative semantics, exact stored content, stable IDs, current pointers, versions, lineage, lifecycle, order, provenance, and compatibility metadata. It supports validated same-archive restoration or staged cross-Workspace import under different identity rules.
4. PostgreSQL backup preserves database/schema state for disaster recovery using deployment-appropriate supported tooling. Database backup and structured archive are both required because neither substitutes completely for the other.
5. Same-archive restoration preserves UUID identities, Scene versions, revision numbers, pointers, lineage, content, representation versions, lifecycle, order, and provenance exactly, subject only to explicit versioned archive/schema migrations.
6. Import into another Workspace is not restoration. It assigns new Strange Novelty IDs, retains source IDs as provenance mappings, discards source grants/authority, stages content for review, and never infers Canon or overwrites by title, timestamp, or revision number.
7. Version 1 restoration is full-Workspace and all-or-nothing. Selected-Scene export may serve author use but is not a complete recovery archive. Restoration into an existing non-empty Workspace is rejected by default.
8. Normal restoration loads into a new isolated non-serving database or empty target, validates before activation, produces a bounded verification report, and requires explicit recently authenticated owner approval. Direct unverified live in-place restore is rejected.
9. Restore activation takes a pre-activation backup of the current live state when applicable, invalidates sessions by default, performs controlled cutover, preserves a rollback path and source evidence, emits bounded security events, and runs post-activation verification.
10. Structured archives exclude live sessions, password/reset credentials, MFA secrets/recovery material, provider/deployment secrets, encryption keys, and environment configuration. Account/grant references are included only as portable identity/relationship data, never automatically trusted authority.
11. Database backups may contain password hashes and authenticator public/protected metadata required for disaster recovery, but restored authentication state is quarantined and deliberately reactivated or reset under later policy. Sessions are invalidated by default.
12. Backup copies and archive storage use authenticated encryption in transit and encryption at rest. Encryption keys are separately stored, least-privileged, rotated/recoverable under later policy, and never embedded in the artifact or Git.
13. Structured archives include an explicit versioned manifest with source Workspace, export operation/time, schema/application compatibility, record counts, stable identifiers or bounded identity inventories, dependency summaries, and cryptographic hashes. Hashes detect corruption; they do not prove authorization or source authenticity.
14. Digital signatures are deferred unless an untrusted-transfer or independent-authenticity threat justifies signing/key lifecycle complexity. Authenticated storage plus cryptographic hashes is the Version 1 baseline.
15. Backups use multiple generations and more than one restore point; one overwritten copy is prohibited. Exact retention, frequency, geographic/offline separation, RPO, RTO, and expiry are later operational decisions.
16. A backup is not considered dependable merely because it was written. Representative isolated restoration and verification must succeed periodically, using synthetic or approved isolated data.
17. Ordinary trash and user-requested logical deletion do not remove retained backup copies. Physical purge cannot promise immediate disappearance from retained/immutable backups. Expiry, key destruction, and purge evidence require explicit retention policy.
18. Corrupt, incomplete, incompatible, cross-Workspace, semantically invalid, or partially loaded restorations fail closed. The system does not silently repair, normalize, reinterpret, partially activate, or best-effort merge authoritative data.
19. Backup, export, restore, and break-glass operators/jobs use bounded technical authority. Technical execution never becomes creative approval or ordinary permission to activate restored content.
20. Long-running operations must be compatible with a later background-job architecture but this ADR selects no queue, storage provider, tooling, or package.

## Terminology and Boundaries

**Human-readable export** is an author-facing rendering intended for reading, editing elsewhere, or personal custody. It may include current content and selected metadata but is not an exact application reconstruction contract.

**Structured archive** is a versioned application-level full-Workspace representation of authoritative semantics. It is portable across compatible deployments and supports validation, same-archive restoration, or staged import.

**Database backup** is a PostgreSQL recovery artifact preserving database state, schema-related state, and operational information required for disaster recovery. It may be logical, physical, snapshot-based, or log-based according to deployment.

**Same-archive restoration** reconstructs the same Workspace/archive identity and preserves stable IDs. It is not duplication or merge.

**Import** creates material in a different target Workspace, normally with new target identities and retained source mappings. It does not preserve source authorization.

**Migration** transforms schema or archive representation under an explicit versioned rule while preserving meaning. **Repair** corrects exceptional corruption through protected operator action. Neither is an author edit or creative approval.

**Disaster recovery** restores service after database, host, storage, deployment, or site failure. **Point-in-time recovery** reconstructs database state near a selected time using a base backup plus transaction-log/WAL capability where deployed.

**Integrity verification** detects corruption/incompleteness and validates relationships/semantics. **Authenticity** provides evidence that a trusted signer/source created an artifact. Hashes alone do not authenticate a maliciously replaced artifact unless the trusted expected hash is protected separately.

**Restore staging** is a non-serving isolated environment. **Activation** is the controlled decision/cutover that makes verified restored state authoritative for serving.

**Backup retention** governs artifact generations and expiry. Application lifecycle governs active/archive/trash/purge states. One does not instantly rewrite the other.

## Backup Principles

- Maintain independent human-readable export, structured archive, and database backup capabilities.
- Protect every artifact as private archive content.
- Preserve multiple recovery points; never rely on a single overwritten backup.
- Keep at least one recovery copy outside the live database's immediate failure domain under later operational policy.
- Use PostgreSQL-supported mechanisms appropriate to the deployment rather than copying live files naively.
- Capture a consistent database state or a documented recoverable sequence.
- Include all authoritative data and required operational metadata; omit only data proven rebuildable or deliberately excluded under recovery policy.
- Detect backup failure, truncation, missing objects, retention failure, encryption/key failure, and unverified age.
- Authorize creation, listing, download, deletion, expiry, restore, and activation independently.
- Treat “written successfully” as artifact creation, not proof of recoverability.
- Test restoration periodically and after material schema, storage, encryption, or deployment changes.
- Keep artifact names, paths, logs, and metrics free of private story titles/content.

Backup jobs use bounded read/backup authority and cannot modify creative state or approve restoration. Export jobs use one authorized Workspace scope. Restore jobs operate only against isolated targets until activation approval.

## Human-Readable Export

Human-readable export gives the owner useful access independent of the running application. Candidate outputs include UTF-8 plain text, Markdown-like presentation, escaped HTML, PDF, and common document formats. No rendering library or final format is selected here.

The export may offer:

- one file per Scene;
- combined manuscript order;
- current Scene content only by default;
- optional selected revision history clearly labeled;
- titles, hierarchy/order, lifecycle labels, and bounded provenance summaries;
- a metadata/index summary; and
- explicit inclusion/exclusion of archived or trashed material.

The authoritative content remains the exact Scene Revision in PostgreSQL. Markdown, HTML, PDF, and document files are derived renderings. Plain-text output applies documented export encoding/line-ending rules and does not redefine stored normalization.

Human-readable exports exclude passwords, hashes, grants as credentials, sessions, MFA/recovery state, security events, provider secrets, deployment configuration, database roles, migration internals, and unrelated operational records.

A selected-Scene or current-manuscript export may be useful and encouraged, but it cannot reconstruct all identity, lineage, current pointers, revisions, provenance, grant state, or recovery metadata. It must never be labeled a complete backup.

Export files use safe generated names/identifiers when titles could leak through paths, download history, object keys, logs, or support systems. An optional private title may appear inside the authorized document where expected.

## Structured Archive

The structured archive is one logical full-Workspace package containing a manifest and versioned record groups/files. This ADR does not select container, compression, serialization, or canonical byte format.

The archive includes:

- archive-format version independent of Django migration names;
- export creation time and Mutation/export operation ID;
- source application/schema compatibility information;
- source Workspace stable ID and bounded display metadata;
- permitted Account identity references and Workspace Grant relationship/state evidence, explicitly non-authoritative on restore until policy validates it;
- Mutation Operation records required to explain included authoritative mutations;
- every included Scene record;
- every Scene Revision for those Scenes;
- explicit Scene current-revision pointers and Scene integer versions;
- revision UUIDs, Scene-scoped revision numbers, predecessor/base/restoration-source references;
- exact stored normalized plain-text content without rerunning normalization;
- content-format and normalization versions;
- lifecycle state and relevant transition timestamps;
- sparse ordering values and scope;
- authoring-source categories and bounded provenance references;
- required integrity metadata;
- record counts and dependency summaries;
- cryptographic hashes at record/file/package levels selected later;
- optional future attachment/object manifests with separate object hashes; and
- compatibility/migration notes and incomplete-operation markers.

The archive preserves exact content values and semantic relationships. It does not infer current state from maximum timestamp, UUID, or revision number when an explicit pointer exists.

The archive excludes live secrets, passwords, recovery-code plaintext or verifiers intended only for live recovery, WebAuthn private material, TOTP seeds, session tokens, reset links/tokens, provider credentials, database credentials, encryption keys, deployment configuration, unrelated logs, and derived data that can be rebuilt.

Password hashes and authenticator metadata are not part of the ordinary portable archive. If a future full-account portable recovery format includes protected verifier state, it requires a separate security decision and cannot activate automatically.

The archive should be deterministic enough that the same logical record has a stable verifiable representation under one archive version. Exact whole-package byte-for-byte canonicalization may remain later work if per-record/file hashes and manifest rules provide reliable verification.

## Database Backup

Database backup is the disaster-recovery boundary for authoritative PostgreSQL state. Deployment may use:

- full logical backup;
- physical/base backup;
- managed-provider snapshot;
- transaction-log/WAL archiving and point-in-time recovery; or
- a tested combination.

Version 1 should prefer operational simplicity appropriate to one owner while retaining multiple restore points and off-host/failure-domain separation. A managed snapshot alone is insufficient unless portability, consistency, retention, encryption, access, restore testing, and provider-failure behavior are accepted.

A complete database recovery must address:

- schema and migration history;
- required extensions/configuration assumptions;
- table data, sequences if any, constraints, and privileges as applicable;
- transaction consistency;
- authentication/account state needed for controlled recovery;
- operational records required to reconcile unfinished work;
- later private object/attachment stores through a coordinated manifest; and
- version compatibility for the target PostgreSQL environment.

Physical backups can offer fast complete recovery and PITR compatibility but are version/platform/deployment sensitive. Logical backups are more inspectable/portable but may restore more slowly and require explicit role/extension/schema handling. The deployment ADR will select the mechanism.

Direct file copies of a running database are rejected unless PostgreSQL's documented backup protocol makes them consistent. Backup success includes tool status, size/count expectations, encryption/storage confirmation, and later restoration verification.

## Backup Scope

The database backup scope is classified as follows:

| Record/data family | Backup treatment | Portable structured archive treatment |
| --- | --- | --- |
| Account | Include required database state | Identity reference only; no live verifier activation |
| Workspace | Include | Include authoritative record |
| Workspace Grant | Include state/history | Include relationship evidence; reauthorize before activation |
| Mutation Operation | Include | Include operations needed for authoritative provenance |
| Scene | Include | Include every record in Workspace archive |
| Scene Revision | Include every retained revision | Include exact content and full retained history |
| Django migration history | Include | Record compatibility version, not raw authority |
| Required schema objects | Include/reconstruct through tested mechanism | Not a substitute for schema migrations |
| Password hashes | May be present in DR backup | Exclude from ordinary portable archive |
| Sessions | May exist in backup; invalidate on recovery | Exclude |
| WebAuthn public/protected metadata | May be present; quarantine/reactivate deliberately | Exclude ordinary archive |
| TOTP/recovery state | Protected backup only if operationally required; reset/quarantine | Exclude |
| Security events | Include where required for incident/recovery history | Include only bounded recovery-relevant records if policy requires |
| Jobs/idempotency | Include enough to reconcile; do not blindly resume | Include only semantic operation references needed for archive |
| Export/restore records | Include | Include bounded manifest/operation evidence where relevant |
| Search/projections/caches | Optional if rebuildable | Omit and rebuild |
| Provider configuration | Non-secret configuration only if recovery requires | Exclude deployment-specific configuration by default |
| Provider/deployment secrets | Separately protected secret recovery; not ordinary DB backup if avoidable | Exclude absolutely |
| Attachments/private objects | Coordinated separate object backup when introduced | Include manifest/object package under later policy |

Authoritative means required to preserve domain truth. Operationally required means needed to resume safely or reconcile incomplete work. Rebuildable means derivable from authoritative records and not necessary in the portable archive. Secret recovery is a separate protected operational capability, never an author-facing archive.

After restore, pending jobs, idempotency states, exports, and external side effects must be reconciled before resumption; they cannot be retried blindly.

## Backup Retention and Generations

Version 1 retention principles are:

- preserve multiple generations, not one overwritten artifact;
- retain a mix of recent and older recovery points under later policy;
- bound retention explicitly and verify expiry/deletion outcomes;
- maintain storage-health, capacity, age, and failed-copy detection;
- separate copies from the live system's immediate host/storage failure domain;
- consider geographic or offline separation based on deployment threat and cost;
- protect encryption keys through a lifecycle that does not make all generations irrecoverable accidentally;
- prevent one compromised application credential from deleting every recovery copy where practical;
- make owner recovery expectations visible and honest; and
- test a representative retained generation, not only the newest.

Exact durations, schedules, generations, regions, offline copies, RPO, RTO, and storage class remain later operational decisions.

Retention does not mirror Scene lifecycle immediately. Active, archived, and trashed records can remain in backups. Physical purge cannot remove data from already immutable/offline generations instantly. The later purge policy must communicate the retention window, provider replicas, encryption-key lifecycle, legal/privacy obligations, and expiry evidence.

Backup deletion is a high-impact authorized action requiring recent authentication/technical controls, bounded events, and protection against deleting the final viable recovery path accidentally.

## Encryption and Secret Handling

All backup/archive transfers use authenticated encryption in transit. Stored database backups and structured archives use encryption at rest appropriate to private manuscript sensitivity. Human-readable exports receive clear protection guidance and may later support optional application-level encryption.

Storage-level/provider encryption is necessary defense in depth but does not replace access control, application-level encryption where exposure requires it, or owner protection after download.

Application-level archive encryption is evaluated but not mandated until custody, recovery, portability, key rotation, loss, sharing, and browser/download workflows are defined. Selecting it prematurely could make archives unrecoverable or couple them to a product/library.

Encryption keys, passwords, service credentials, signing keys, provider tokens, and database credentials:

- remain outside Git;
- are never stored inside the artifact they protect;
- are separately scoped for backup, export, and restore roles;
- are inaccessible to ordinary browser sessions;
- do not appear in logs, manifests, filenames, metrics, or error bodies;
- require later rotation, revocation, recovery, and break-glass procedures; and
- must not make one lost key silently destroy every recovery generation.

Least-privileged backup credentials may read consistent backup state and write only to the intended destination. Restore credentials target isolated environments and do not imply live activation authority.

## Archive Manifest and Integrity

Version 1 uses a versioned integrity manifest with cryptographic hashes. The manifest includes:

- archive-format version;
- source application/schema compatibility identifiers;
- source Workspace ID;
- export operation ID and creation time;
- record counts by type;
- stable ID inventories or hashed/partitioned inventories appropriate to scale/privacy;
- dependency summaries and required record groups;
- content-format and normalization versions present;
- per-record or per-file cryptographic hashes;
- object/attachment hashes when later included;
- manifest/package hash or root digest;
- incomplete/cancelled operation status;
- hash/serialization algorithm identifiers; and
- optional signer/signature metadata only if signatures are later selected.

Cryptographic hashes detect accidental corruption and mismatches. Counts detect omissions/duplication. Stable IDs and dependency summaries support relationship validation. None grants authorization or proves Canon.

Checksums using weak accidental-error algorithms alone are insufficient for hostile/tamper-aware validation. Cryptographic hashes plus authenticated storage are selected as the baseline.

Digital signatures could authenticate an archive independently of its storage location, but introduce signing-key custody, rotation, revocation, signer identity, expiry, offline verification, and compromise recovery. They are deferred until untrusted transfer or external verification requires them.

The expected manifest/root hash must be protected with the archive's authenticated metadata or separately trusted channel. A malicious actor able to replace both artifact and unprotected manifest can defeat hash-only authenticity.

Manifest verification precedes parsing/applying records. Semantic validation follows; hashes cannot prove valid Workspace scope, lineage, pointers, lifecycle, authorization, or compatibility.

## Authentication, Session, and MFA State

Authentication material receives different treatment from creative archive semantics.

- Structured archives exclude live passwords/verifiers, reset tokens, sessions, WebAuthn private material, TOTP seeds, recovery codes/verifiers, and active MFA/recovery state.
- Account stable references and Grant relationships may be included to preserve archive semantics but confer no target authorization.
- Database backup may contain password hashes and authenticator public/protected state because it preserves database state; that state is quarantined after restore.
- Sessions are invalidated by default after disaster recovery, archive restoration, or activation.
- Password/reset/MFA/recovery material is deliberately revalidated, rotated, reset, or re-enrolled under later recovery policy.
- Source Account identity does not automatically authorize the target operator or owner.
- Restored Grants are validated structurally but require current owner/account recovery policy before serving.

WebAuthn private keys never exist server-side. Provider/deployment secrets remain outside both portable archives and ordinary author exports. If secret recovery is needed for disaster recovery, it uses a separate protected mechanism and rotation after recovery.

Authentication incompatibility fails closed; restoration may preserve the creative Workspace while requiring new owner enrollment through protected recovery. Account disablement and Grant revocation never delete the archive.

## Restoration Modes

Version 1 recognizes:

- **Database disaster recovery:** restore PostgreSQL state to compatible infrastructure, then quarantine/verify before serving.
- **Application archive restoration:** reconstruct the same Workspace from a structured archive in an empty isolated target.
- **Point-in-time recovery:** deployment-dependent reconstruction to a selected transaction point, followed by the same verification/activation boundary.
- **Cross-Workspace import:** stage archive/legacy material into another Workspace with new IDs; not restoration.

Routine Version 1 restoration is full-Workspace and all-or-nothing. Partial selected-Scene restoration is rejected because Scenes depend on revision history, operations, ordering, future hierarchy/links/states, and Workspace semantics. A selected Scene may be exported for reading or staged import, but not called complete recovery.

In-place restore over a live serving database is rejected as normal behavior. Restoring to a new database or empty target provides evidence preservation, validation, rollback, and cutover control.

Restoration into an existing non-empty Workspace is rejected by default because identity collisions, current-state conflicts, lineage merging, lifecycle, grants, and provenance cannot be reconciled safely by ordinary restore.

## Same-Archive Restoration

Same-archive restoration proves and preserves the source Workspace/archive identity. It preserves exactly:

- Account/Grant identity references as data, pending authorization reactivation;
- Workspace UUID;
- Mutation Operation UUIDs and bounded provenance;
- Scene UUIDs;
- every Scene Revision UUID and exact content value;
- Scene current pointer and integer version;
- revision numbers;
- predecessor/base/restoration-source lineage;
- content-format and normalization versions;
- lifecycle states/timestamps;
- ordering values/scopes; and
- integrity metadata.

Historical content is not re-normalized. Archive migration may transform representation only through an explicit versioned, validated process that preserves source evidence and reports changes. It cannot silently rewrite immutable revisions.

The target is a new isolated database or empty target Workspace. If schema/application versions differ, compatible forward archive migrations operate on a copy/staging representation, never destructively on the sole source artifact.

Restored current state comes from explicit pointers, not maximum timestamps, UUID order, or revision number. Same-archive restoration preserves Scene version values unless a documented migration explicitly changes their semantics.

## Import into Another Workspace

Cross-Workspace import is a staged transformation, not identity-preserving restoration.

It must:

- assign new target Workspace-scoped UUIDs;
- retain source Workspace/type/ID/archive references as provenance mappings;
- never preserve source Grant as target authority;
- never activate source sessions, MFA, recovery, provider, or deployment state;
- classify imported creative material as Imported content;
- stage validation, transformation, warnings, and owner review before apply;
- avoid inferring Canon, truth, approval, current target state, or permission;
- avoid matching/overwriting by title, revision number, timestamp, path, or name;
- avoid silently merging revision chains;
- use ordinary target authorization/concurrency/provenance services on apply; and
- preserve source evidence without copying secrets or unnecessary manuscript duplicates.

Legacy Story Engine input is always untrusted import. Old integer IDs remain source provenance only. Old settings, credentials, sessions, permissions, and implied Canon are excluded.

Restoring a copy into a new database while preserving the same Workspace identity is still same-archive restoration. Creating a new Workspace identity is import/duplication and requires new IDs unless a later explicit clone operation defines a mapping.

## Restoration Staging

The normal restore flow is:

1. obtain an explicitly authorized backup or structured archive through a protected channel;
2. preserve the original artifact and expected manifest/hash evidence read-only;
3. verify artifact type, source, size, archive/schema version, encryption access, and integrity manifest before full parsing;
4. restore/load into an isolated non-serving database or empty target;
5. apply only explicit compatible migrations to a copy/staged target;
6. run database/schema structural validation;
7. run application semantic validation;
8. verify counts, identities, Workspace isolation, grants, operations, Scenes, revisions, pointers, versions, lineage, content, lifecycle, order, and provenance;
9. quarantine/invalidate sessions and unsafe authentication/provider state;
10. rebuild and validate derived data from authoritative records;
11. produce a bounded verification report without manuscript bodies;
12. require explicit recently authenticated owner activation approval, separate from technical execution;
13. take a pre-activation backup of current live state when replacing service;
14. activate through controlled cutover with rollback path; and
15. run post-activation authenticated verification and record bounded security/recovery events.

The staging environment is access-controlled and treated as production-sensitive because it contains the full archive. It is not ordinary development/CI and must not use broad telemetry or unmanaged copies.

A dry run performs all feasible load/verification steps without activation. Dry-run success is strong evidence but does not replace tested cutover/rollback procedures.

## Restoration Verification

Verification must establish at least:

- archive/schema/application compatibility;
- expected record groups and manifest counts;
- cryptographic hash agreement;
- unique non-null stable IDs and no duplicate primary identities;
- one valid Workspace scope for the full archive;
- valid Account/Grant references and grant states without automatic authority;
- no cross-Workspace Scene, Revision, Operation, lineage, or pointer references;
- every Scene belongs to the Workspace;
- every Revision belongs to its Scene and Workspace;
- every committed Scene has a valid current Revision belonging to it;
- Scene versions satisfy accepted constraints and match archive values;
- revision numbers are valid and unique within Scene;
- predecessor/base/restoration references remain within Scene/Workspace;
- no prohibited lineage self-reference and no detected cycles/broken chains;
- exact revision content values match hashes and are not normalized again;
- supported content-format and normalization versions;
- valid lifecycle values and coherent transition timestamps;
- valid ordering values/scopes and no prohibited collisions;
- valid Mutation Operation references and source categories;
- no unexpected/missing authoritative records;
- derived data can be discarded/rebuilt and agrees with authoritative sources;
- sessions are invalidated and authentication/MFA state is quarantined/compatible;
- portable archives contain no prohibited secrets/authentication material;
- job/idempotency/external-effect states are reconciled before resumption; and
- no serving/activation occurred before approval.

Automated validation provides repeatability and complete relationship scanning. Manual verification confirms representative author-visible Scenes, Unicode/line breaks, ordering, lifecycle, revision history, export behavior, authorization, and operational readiness. Both are required; neither alone is sufficient.

The report contains counts, categories, hashes/statuses, version data, bounded identifiers/correlation references, failures, warnings, and migration transformations. It does not copy manuscript text, credentials, tokens, or private filenames.

## Restore Activation

Activation is a separate high-impact operation after successful verification.

It requires:

- explicit owner authorization and recent authentication;
- review of the bounded verification/migration report;
- a second deliberate confirmation for destructive replacement/cutover;
- confirmation of target Workspace/archive identity and recovery point;
- attributable technical operator execution or bounded restore service identity;
- pre-activation backup/snapshot of current live state where applicable;
- controlled traffic stop/read-only/cutover behavior defined later;
- default session invalidation and credential/secret review;
- retained original artifact and rollback target;
- bounded security and restoration events without manuscript content; and
- post-activation authenticated checks of content, history, scope, export, and ordinary use.

Owner approval authorizes activation; it does not cause database actions directly from the browser without server validation. Technical operators may execute approved recovery but cannot infer creative approval, Canon, or permission to inspect content broadly.

A bounded break-glass path may permit recovery when ordinary authentication is unavailable, but only under ADR-0005's separately documented protected procedure with evidence, rotation, session revocation, notification, and owner review.

Activation failure returns to the preserved prior deployment/backup when safe. No failed target remains partially serving.

## Failure, Rollback, and Recovery Evidence

Restoration fails closed on:

- corrupt or undecryptable backup;
- incomplete archive/package;
- manifest/hash/count mismatch;
- missing required records or revisions;
- invalid/foreign current pointer;
- duplicate IDs;
- cross-Workspace references;
- invalid lineage, revision number, lifecycle, order, provenance, or grant state;
- incompatible archive/schema/application version;
- unsupported content/normalization version;
- authentication-state incompatibility;
- migration transformation failure;
- interrupted load;
- partial validation;
- derived rebuild failure that blocks safe use; or
- inability to preserve rollback/source evidence.

There is no silent best-effort partial recovery, automatic content repair, identity regeneration, pointer inference, chain collapse, or normalization of old content. A safe tool may report possible repair steps, but repair requires a separate explicit procedure and leaves source evidence unchanged.

Interrupted staging is discarded or resumed only through a documented idempotent process. It never becomes live by presence alone.

Rollback after cutover restores the preserved pre-activation service state through a tested procedure. Rollback does not erase evidence of the failed restoration and does not retry external effects blindly.

Recovery evidence includes source artifact identity/hash, target identity, versions, operator/owner approvals, verification report, migration report, activation/cutover status, rollback status, session/credential actions, and bounded timestamps. It excludes manuscript bodies and secrets.

## Background Job and Operator Authority

Backup, export, verification, and restore work may be long-running and must fit the later background-job/idempotency architecture.

Authority is separated:

- backup job: read consistent required database/object state and write to one approved protected destination;
- human-export job: read only the authorized Workspace/revision scope and write one private artifact;
- structured-archive job: read complete authorized Workspace semantics and produce manifest/package;
- verification job: read staged artifact/target and emit bounded findings;
- restore job: write only to approved isolated target before activation;
- activation operator/service: perform approved cutover with separate authority;
- break-glass operator: narrowly recover access/execution under documented emergency controls.

No job reuses an unrestricted browser session, infers authority from an artifact ID, accesses other Workspaces, or gains Canon/creative approval. Jobs revalidate current state and operation authorization at meaningful boundaries.

Exact queue, runner, schedule, storage integration, retry, idempotency schema, cancellation, progress, and service credentials remain later decisions.

## Deletion, Purge, and Backup Expiry

Active, archived, and trashed application states remain in database backups and full structured archives according to scope. Ordinary trash is reversible and does not trigger artifact deletion.

User-requested physical purge is distinct from backup expiry. Purge removes live authoritative records only through a later approved dependency-aware workflow. Existing retained backups, immutable generations, provider replicas, offline copies, and already downloaded exports may continue to contain the data until their retention expires or media/keys are destroyed.

The UI/procedure must communicate this honestly. It cannot promise immediate erasure from every recovery copy.

Later retention policy must define:

- how purge requests interact with new backup creation;
- backup generation expiry and deletion verification;
- encryption-key destruction implications;
- legal/privacy retention obligations;
- offline/owner-held copies outside application control;
- purge evidence without manuscript content; and
- recovery consequences of deleting all copies.

Backup expiry is an operational retention event, not a domain lifecycle transition. It requires authorization and must not silently delete the last dependable restore point.

## Recovery Objectives

Deployment and operations require later explicit decisions for:

- Recovery Point Objective (maximum tolerable data loss);
- Recovery Time Objective (maximum tolerable outage);
- backup/database-log frequency;
- structured archive frequency;
- restoration-test frequency;
- retention duration/generation schedule;
- geographic/failure-domain separation;
- offline copies;
- maximum artifact age before warning/failure;
- owner notification and recovery expectations; and
- costs and operational staffing.

This ADR sets no exact values because hosting, data volume, writing cadence, provider capabilities, and owner tolerance are undecided. The operational deployment ADR must select and test them before real private content depends on the system.

Database backup frequency and structured archive frequency may differ. Human-readable export remains owner-triggered/convenience and is not an RPO mechanism.

## Django Application Boundary

Django application/query services authorize and scope export/archive requests, create bounded operation records, select authoritative records consistently, construct manifests, validate structured archives, orchestrate semantic restoration checks, and require recent authentication/activation intent.

Django serializers or custom archive encoders may later produce records, but ordinary framework fixture serialization is not automatically the portable archive contract. Archive versions must remain stable and explicit across model refactors.

Application validation complements PostgreSQL constraints by checking archive compatibility, identity mode, lineage cycles, lifecycle semantics, source categories, grants, authorization, and restore activation.

Django never accepts an archive path, object key, Workspace ID, hash, or successful job state as authority by itself. Browser downloads use protected, short-lived, single-purpose access.

No model, serializer, command, job, view, route, archive implementation, or package is selected here.

## PostgreSQL Boundary

PostgreSQL-supported backup/restore mechanisms provide database consistency according to the selected deployment. The future operational design must account for server/version compatibility, roles, privileges, extensions, schema, migration table, transaction logs, snapshot consistency, and recovery target.

PostgreSQL constraints validate core structural relationships after restore. Application verification adds semantics that foreign keys/checks cannot express, including lineage cycles, authorization reactivation, archive completeness, and current-state meaning.

Logical backup, physical backup, snapshots, and PITR have different portability and recovery properties. None is selected until deployment is known. A supported tested combination is required.

Backup/restore database roles are separate from ordinary application roles where practical. Technical database restore capability does not authorize serving or creative changes.

No PostgreSQL configuration, connection, command, script, object, role, or backup mechanism is created by this ADR.

## Rationale

Three distinct outputs satisfy different owner needs: readable access, portable application semantics, and infrastructure disaster recovery. Calling any one of them all three would hide omissions and create false confidence.

Full-Workspace archives preserve relational invariants more safely than selected-record restoration. Exact same-archive identity preservation keeps links, lineage, pointers, versions, and provenance meaningful; new IDs for cross-Workspace import prevent identity/authority collision.

Isolated staging and verification prevent corrupt, hostile, incomplete, or incompatible artifacts from replacing the live archive. Separate activation preserves owner authority and a rollback path.

Cryptographic hashes plus manifests provide practical corruption detection without prematurely creating signing-key infrastructure. Authenticated/encrypted storage protects confidentiality while keeping key custody a separately reviewable operational decision.

Multiple generations and verified restore tests address the primary backup failure mode: an artifact that exists but cannot recover the application. Explicit session/secret handling prevents disaster recovery from silently reopening compromised access.

## Decision Criteria

Options are evaluated against:

1. complete preservation of authoritative identity, content, history, and Workspace scope;
2. owner access independent of the running application;
3. disaster recovery and infrastructure portability;
4. integrity, compatibility, and semantic verification;
5. privacy, encryption, least privilege, and secret isolation;
6. safe authentication/session handling after recovery;
7. explicit owner approval separate from technical execution;
8. all-or-nothing failure and rollback safety;
9. import/restoration identity correctness;
10. multiple restore points and honest deletion/retention behavior;
11. maintainability for one owner and small Version 1;
12. future attachments/subsystems without provider lock-in; and
13. testable RPO/RTO and recovery procedures later.

## Alternatives Considered

### Only human-readable export

Rejected. It protects access to prose but cannot reconstruct IDs, pointers, history, grants, provenance, lifecycle, or schema.

### Only database backup

Rejected. It supports disaster recovery but is deployment/version sensitive and not a stable portable application contract or author-readable exit path.

### Database backup plus structured archive

Selected, with human-readable export also required. The redundancy serves distinct purposes and offers cross-checking/recovery options.

### Full logical backup

Portable and inspectable across compatible PostgreSQL versions, but can be slower and requires careful roles/extensions/schema handling. Candidate deployment mechanism.

### Physical backup

Fast and suitable for full recovery/PITR, but tightly coupled to PostgreSQL/deployment compatibility. Candidate mechanism.

### Managed-provider snapshot only

Rejected as the sole strategy because provider access/failure, consistency, portability, retention, and tested restoration remain risks.

### Point-in-time recovery

Valuable for reducing data loss and recovering before corruption, but requires WAL/log operations and deployment maturity. Evaluate later alongside base backups.

### One overwritten backup

Rejected because corruption, compromise, or unnoticed failure can destroy the only recovery point.

### Multiple generations

Selected. It increases storage/key/retention complexity but protects against delayed discovery.

### Live in-place restore

Rejected as normal behavior because it destroys rollback evidence and exposes partial/corrupt state.

### Isolated restore then activation

Selected. It costs additional storage/time but enables validation and controlled cutover.

### Exact same-archive identity preservation

Selected for restoration. Identity is part of the archive's meaning.

### Always assign new IDs

Rejected for restoration because it breaks references/provenance. Selected in principle for import into a different Workspace.

### Full-Workspace archive

Selected as the complete structured recovery unit. It preserves cross-record consistency.

### Selected-Scene archive

Useful as author export or future import input, but rejected as complete restoration because dependencies/history may be omitted.

### Restore into existing non-empty Workspace

Rejected by default due to identity, lineage, ordering, grant, and current-state collision.

### Restore into empty target/new database

Selected for staging and same-archive recovery.

### Direct activation after load

Rejected. Loading does not prove integrity or semantics.

### Verification report before activation

Selected. It supports owner review, bounded evidence, and rollback decisions.

### Checksums only

Rejected if they mean weak accidental-error checks without semantic validation/authenticated metadata.

### Cryptographic hashes plus manifest

Selected baseline. Provides practical corruption/tamper detection when expected metadata is protected.

### Digital signatures

Deferred until independent authenticity/untrusted transfer justifies key-management complexity.

### Archive-level encryption

Potential future option for portable artifacts. Deferred until owner key custody/recovery and library portability are designed.

### Storage-level encryption only

Required baseline defense but may not protect downloaded/transferred copies or privileged provider access. It may need application-level complement later.

### Include sessions

Rejected for portable archives. Database backups may contain session rows, but restored sessions are invalidated.

### Invalidate sessions

Selected default after restore/activation to contain theft, stale state, and environment changes.

### Include provider secrets

Rejected. Secrets use separate recovery/rotation processes.

### Exclude provider secrets

Selected for human exports, structured archives, and ordinary content backup scope.

### Rebuild derived data

Selected. Search/render/count/backlink projections are verified/rebuilt from authoritative records.

### Back up derived data

Optional for performance in database backup, but never required in structured archive when rebuildable.

### Automatic repair

Rejected. It can hide corruption and alter authority/history. Report and use explicit repair procedure.

### Fail-closed restoration

Selected. Invalid or incomplete state never becomes authoritative.

### Partial restoration

Rejected for ordinary Version 1 recovery due to dependency inconsistency.

### All-or-nothing restoration

Selected for the full Workspace.

### Operator-only approval

Rejected. Technical capability is not owner authorization.

### Owner approval plus technical execution

Selected, with break-glass exception under documented recovery when ordinary owner authentication is unavailable.

### Backup successful when written

Rejected. Writing proves only artifact creation.

### Backup dependable after verified restore

Selected. Periodic representative recovery provides evidence.

## Comparative Assessment

### Backup and export strategy

| Strategy | Human access | Exact semantics | Disaster recovery | Decision |
| --- | --- | --- | --- | --- |
| Human export only | Strong | Weak | Weak | Rejected alone |
| DB backup only | Weak | DB-exact | Strong | Rejected alone |
| Structured archive only | Moderate | Strong | Moderate | Rejected alone |
| Human + archive + DB backup | Strong | Strong | Strong | Selected |

### Restore target strategy

| Target | Validation safety | Rollback | Collision risk | Decision |
| --- | --- | --- | --- | --- |
| Live in-place | Low | Low | High | Rejected normal path |
| Existing non-empty Workspace | Moderate/low | Complex | Very high | Rejected default |
| Empty target Workspace | High | Strong | Low | Selected archive staging |
| New isolated database | Highest | Strong | Low | Preferred staging/DR |

### Identity behavior

| Operation | Workspace identity | Record IDs | Authority |
| --- | --- | --- | --- |
| Same-archive restore | Preserve | Preserve exactly | Revalidate before activation |
| Cross-Workspace import | New target | New IDs + mappings | Target owner review |
| Legacy Story Engine import | New target | New IDs; legacy IDs provenance | No inherited authority |
| Human export | Informational | May include references | Grants none |

### Integrity verification

| Strategy | Corruption detection | Authenticity | Semantic validity | Decision |
| --- | --- | --- | --- | --- |
| Counts only | Weak | None | Weak | Insufficient |
| Weak checksums | Moderate accidental | None | None | Insufficient |
| Cryptographic hashes + manifest | Strong mismatch detection | Storage-dependent | Needs validators | Selected baseline |
| Digital signature | Strong + signer proof | Strong if keys trusted | Needs validators | Deferred |

### Session and authentication handling

| Approach | Continuity | Compromise/staleness risk | Decision |
| --- | --- | --- | --- |
| Reactivate all restored sessions | Convenient | Very high | Rejected |
| Preserve hashes/factors and trust automatically | Convenient | High | Rejected |
| Quarantine auth, invalidate sessions, revalidate | More friction | Lowest | Selected |
| Omit all account references | Simple | Breaks grant/archive meaning | Not selected |

### Full versus partial restoration

| Scope | Consistency | Flexibility | Decision |
| --- | --- | --- | --- |
| Full Workspace | Strong | Lower | Selected V1 restore |
| Selected Scene | Dependency risk | High | Export/import only |
| Best-effort partial load | Weak | Superficially high | Rejected |
| All-or-nothing apply | Strong | Clear failure | Selected |

### Retention strategy

| Strategy | Delayed corruption recovery | Cost | Decision |
| --- | --- | --- | --- |
| One overwritten copy | Weak | Lowest | Rejected |
| Multiple generations | Strong | Higher | Selected |
| Live-host copies only | Weak failure separation | Low | Insufficient |
| Off-host/geographic/offline mix | Strongest | Higher/operational | Later policy requirement based on risk |

## Evidence

### Repository evidence

- Product vision/principles require privacy, ownership, useful export, practical backup, tested restoration, and service-independent exit paths.
- Version 1 scope is not complete until representative backup restoration succeeds.
- The roadmap requires export, backup verification, restoration, and known data-loss risk review before Phase 1 completion.
- Architecture documents distinguish authority, derived data, export, backup, import, migration, restoration, secrets, logs, and bounded jobs.
- ADR-0001 through ADR-0008 establish the server boundary, PostgreSQL, UUIDs, immutable revisions, authorization, normalized content, Workspace-scoped schema, and physical constraints/migrations.
- The architecture handoff names this ADR as the next dependency after physical schema.
- The Story Engine audit found incomplete structured export, raw database copies, credential co-location, missing manifests, and no verified restoration; it recommends not reusing those mechanisms.

### Official guidance reviewed conceptually

The decision is informed by current official guidance without binding to exact versions:

- [PostgreSQL backup and restore](https://www.postgresql.org/docs/current/backup.html)
- [PostgreSQL SQL dump](https://www.postgresql.org/docs/current/backup-dump.html)
- [PostgreSQL file-system backup](https://www.postgresql.org/docs/current/backup-file.html)
- [PostgreSQL continuous archiving and PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [Django serialization](https://docs.djangoproject.com/en/stable/topics/serialization/)
- [Django migrations](https://docs.djangoproject.com/en/stable/topics/migrations/)
- [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Django security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

This guidance supports consistent PostgreSQL backup mechanisms, tested restores, migration/version awareness, least privilege, encryption, independent secret custody, deny-by-default authorization, and exclusion of sensitive data from logs.

### Evidence still required

Before acceptance or operational implementation:

- select deployment and supported PostgreSQL/Django versions;
- classify every actual table/object as authoritative, operational, derived, secret, or externally stored;
- define structured archive schema/container/serialization and deterministic hashing rules;
- prototype full-Workspace archive round trip using synthetic data;
- select database backup/PITR mechanism after hosting choice;
- define backup/object-store/restore roles and access separation;
- decide encryption/key custody and optional archive encryption;
- threat-model whether signatures are needed;
- define retention generations, RPO, RTO, schedules, regions, offline copies, and alerts;
- define authentication quarantine/reset/re-enrollment behavior after restore;
- define staging/cutover/rollback and break-glass procedures;
- define manifest/semantic validators and bounded reports;
- test corrupt, incomplete, malicious, cross-Workspace, incompatible, and interrupted restores;
- verify exact Unicode/content/hash preservation without re-normalization;
- verify derived rebuild and job/external-effect reconciliation;
- define attachment/object coordination before files are introduced; and
- perform periodic representative restore exercises after implementation.

## Consequences

### Positive

- The owner receives readable access, portable semantics, and disaster recovery rather than one ambiguous artifact.
- Stable IDs and complete revision history survive same-archive restoration.
- Cross-Workspace import cannot inherit source authority or collide silently.
- Isolated verification prevents invalid artifacts from replacing live state.
- Hash manifests detect corruption and omissions.
- Session invalidation and secret exclusion reduce post-recovery account takeover.
- Multiple generations protect against delayed corruption/ransomware/operator error.
- Full-Workspace restoration preserves relational consistency.
- Derived data can be omitted/rebuilt, reducing portable archive coupling.
- Verified restore testing turns backup claims into evidence.

### Negative

- Three artifact classes add implementation, documentation, and owner-education work.
- Full-Workspace archives can be large and contain extensive sensitive history.
- Multiple generations increase storage, encryption-key, retention, and deletion complexity.
- Isolated staging requires extra infrastructure/storage and extends recovery time.
- Session invalidation and authentication quarantine add recovery friction.
- Deterministic manifests and semantic validation require substantial tooling.
- Full-Workspace-only restore is less flexible than selected-record recovery.
- New-ID import mappings complicate provenance and relationship transformation.
- Protective fail-closed behavior may leave the application unavailable longer.
- Database backup portability depends on selected PostgreSQL/deployment mechanism.

### Neutral or Operational

- Digital signatures remain optional future enhancement.
- Exact archive encryption may differ from database/provider encryption.
- Database backup may retain derived data while structured archive omits it.
- Backup expiry does not equal immediate application purge.
- Human-readable export formats can evolve independently.
- RPO/RTO values await deployment evidence.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Export is mistaken for backup | False recovery confidence | Distinct names/UI/docs and restore tests | Owner may still retain only exports |
| Backup exists but cannot restore | Permanent loss/downtime | Periodic isolated verified restore | Failures can emerge between tests |
| Backup omits authoritative table/object | Incomplete archive | Explicit scope inventory, manifest counts, schema-change review | Future subsystems can regress coverage |
| Archive includes secrets | Credential compromise | Denylist plus allowlisted schema, scans/tests, separate secret recovery | New secret fields may be missed |
| Backup stolen | Complete archive disclosure | Encryption, least privilege, access events, key separation | Compromised key/operator can expose data |
| Encryption key lost | Backups unrecoverable | Separate redundant protected key recovery and rotation tests | Key custody remains a single critical system |
| Hash manifest replaced with artifact | False integrity | Authenticated storage/protected expected hash; signatures if threat requires | Storage-admin compromise remains |
| Restore crosses Workspace boundaries | Private data/authority corruption | Composite constraints, semantic validation, full-Workspace scope | Validator bugs remain possible |
| Current pointer inferred incorrectly | Wrong manuscript state | Restore explicit pointer only and validate | Corrupt source pointer causes fail-closed outage |
| Content renormalized | Immutable history corruption | Restore exact stored values and versions; hash verification | Archive migration can still be buggy |
| Sessions reactivate | Account takeover/stale authorization | Invalidate by default; quarantine auth state | Recovery access must be re-established |
| Provider secrets restore | External compromise/cost | Exclude; rotate/reprovision separately | Service may remain unavailable longer |
| Restore activated prematurely | Corrupt live archive | Separate verification report and recent owner approval | Break-glass pressure may bypass process |
| Operator assumes creative authority | Unauthorized content decisions | Separate technical/owner roles and bounded events | One-owner operation limits separation |
| In-place restore destroys rollback | Irrecoverable failure | New isolated target and pre-activation backup | Cutover can still fail |
| Partial restore accepted | Broken references/history | All-or-nothing full Workspace and fail closed | Recovery flexibility reduced |
| Old backups retain purged content | Privacy/expectation mismatch | Honest retention policy, expiry evidence, key lifecycle | Offline/downloaded copies remain outside control |
| One backup generation is corrupted | Data loss | Multiple generations and older test samples | Correlated compromise can affect all online copies |
| Background retry duplicates artifacts/effects | Cost/confusion | Later idempotency/job architecture and reconciliation | Unknown external outcomes remain |
| Recovery report leaks manuscripts | Secondary disclosure | Counts/hashes/categories only, access control | IDs/metadata remain sensitive |

## Security and Privacy Review

- Security-sensitive: Yes; backup/archive artifacts may contain the complete private creative archive.
- Primary references: `docs/architecture/security.md`, `docs/architecture/data-model.md`, ADR-0001 through ADR-0008.
- Additional references: product vision, principles, scope, roadmap, AI context, integrations, architecture handoff, and Story Engine audit.

### Assets and threats

Assets include database state, archives, manuscript revisions, identities, grants, provenance, authentication metadata, manifests, encryption/signing keys, storage credentials, restore environments, and recovery evidence. Threats include theft, insider access, ransomware, deletion, corruption, truncation, stale copies, cross-Workspace injection, malicious archives, secret leakage, premature activation, key loss, and unverified backups.

### Access and authorization

Browser access is limited to explicitly authorized operation initiation/status/download. Backup storage is not browser-addressable. Artifact URLs are short-lived/single-purpose if used. Jobs/operators have least privilege and attributable access.

Recent owner authentication and explicit intent govern export of the complete archive, backup deletion, restore initiation, and activation. Technical database/storage capability is not approval.

### Confidentiality and logging

Artifacts use encrypted transit/storage and safe generated names/object keys. Logs, traces, metrics, security events, alerts, exception reports, job payloads, and verification reports exclude manuscript bodies, credentials, full paths, private titles, tokens, encryption material, and archive contents.

IP/operator/access metadata is sensitive and retained narrowly. Staging environments disable ordinary analytics/telemetry that could capture data.

### Recovery and revocation

After disaster recovery, sessions are revoked, provider/deployment secrets reviewed/rotated as appropriate, external jobs/effects reconciled, and operator/break-glass credentials closed or rotated. Compromised backup/storage credentials are revoked without deleting the only recoverable artifacts prematurely.

### Required verification

Before Version 1 acceptance, synthetic tests must cover:

- authorization/recent-authentication for create/list/download/delete/restore/activate;
- exact archive scope and exclusion of secrets/sessions;
- safe filenames, paths, object keys, logs, metrics, and errors;
- encryption/key access failure and stolen-artifact assumptions;
- manifest count/hash mismatch, missing/duplicate records, and tampering;
- archive bombs, malformed data, incompatible versions, and parser limits;
- same-archive ID/pointer/version/content preservation;
- cross-Workspace import new-ID mapping and no inherited grants/Canon;
- invalid Workspace, lineage, current pointer, lifecycle, order, operation, and revision-number rejection;
- session invalidation and authentication quarantine;
- isolated staging, no accidental serving, owner approval, cutover, and rollback;
- derived-data rebuild and disagreement handling;
- interrupted jobs/restores and no partial activation;
- backup generations, expiry, deletion protection, and restore of older points; and
- periodic representative authenticated application checks after restore.

### Residual risk

Any usable backup contains highly sensitive data and creates another exposure surface. Authorized operators/providers and key custodians can potentially access it. A correlated compromise may affect live data, online backups, keys, and manifests. Recovery may be slow, and fail-closed validation may prolong outage. Owner-held downloaded exports remain outside application control.

## Product and Architecture Alignment

### Product alignment

The decision preserves owner control, exit paths, private custody, exact history, recovery from system failure, and honest deletion expectations.

### Scope alignment

Version 1 requires useful export, backup creation/verification, documented restoration, and a representative restore test. This ADR establishes those boundaries without implementing later publishing, collaboration, or provider integrations.

### ADR alignment

- ADR-0001: browser, external services, and jobs receive bounded authority.
- ADR-0002: Django services orchestrate authorized archive/restore semantics.
- ADR-0003: PostgreSQL backup, constraints, migration, and restoration verification remain central.
- ADR-0004: stable IDs, full revisions, pointers, versions, lineage, and idempotency survive recovery.
- ADR-0005: recent authentication, session revocation, recovery, and administrator/owner separation govern activation.
- ADR-0006: exact normalized content and representation versions are preserved without re-normalization.
- ADR-0007: Workspace scope, lifecycle, order, provenance, and supporting boundaries remain distinct.
- ADR-0008: native UUID keys, initial empty revisions, composite constraints, Mutation Operation, migration order, and protective deletion shape archive/backup validation.

### Architecture alignment

The model keeps derived data rebuildable, imports untrusted, AI/providers non-authoritative, secrets outside artifacts, logs bounded, and restoration isolated and explicit.

### Normative-document impact

If accepted, data-model, security, export, backup, restoration, operations, and roadmap documents should be reconciled with the three-artifact model, full-Workspace archive, hash manifest, isolated verification, session invalidation, and retention boundaries. The ADR index should then be updated. No other document is changed by this Proposed ADR.

## Migration and Portability

The structured archive is versioned independently of Django migration filenames so it can survive internal refactors. It records compatibility and representation versions sufficient to select explicit migrations.

Archive migration:

- operates on a preserved source/copy;
- is deterministic and versioned where practical;
- reports every transformation, warning, and unsupported feature;
- preserves stable identity for same-archive restoration;
- never silently rewrites content, lineage, Canon, or provenance;
- fails without partial activation; and
- retains original evidence and rollback path.

Database backups restore to compatible PostgreSQL according to selected tooling. Migration from one provider/host to another validates the same semantic invariants before activation.

Cross-Workspace import creates new IDs and mapping provenance. Legacy Story Engine content never becomes schema-compatibility authority.

Future attachments/private objects add a manifest-addressed object backup/archive layer whose hashes and references must reconcile with the database. No external provider becomes the sole custodian.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Inventory every implemented/future table and object by authoritative, operational, derived, secret, or external status before backup implementation.
- [ ] Define human-readable export scope/options and safe naming.
- [ ] Define structured archive record schema, versioning, container/serialization, and compatibility policy.
- [ ] Define deterministic per-record/file hashing and manifest/root-digest rules.
- [ ] Threat-model whether digital signatures are required.
- [ ] Select deployment-specific PostgreSQL logical/physical/PITR backup mechanisms later.
- [ ] Define coordinated private-object backup before attachments exist.
- [ ] Define storage/provider access, encryption, key custody, rotation, and recovery.
- [ ] Set retention generations, schedules, RPO, RTO, restore-test frequency, geographic/offline separation, and alerts.
- [ ] Define authentication quarantine, session invalidation, credential rotation, and owner re-enrollment after restore.
- [ ] Define isolated staging, compatibility migration, verification, activation, cutover, and rollback procedures.
- [ ] Define bounded verification report/security-event schemas.
- [ ] Define backup/export/restore job authority and idempotency after the job ADR.
- [ ] Define purge/backup-expiry interaction and owner communication.
- [ ] Define new-ID cross-Workspace import mapping and legacy Story Engine staging in a later import ADR.
- [ ] Test archive round trip and database restore with synthetic representative Unicode, revisions, lifecycle, ordering, provenance, and grants.
- [ ] Test corrupt/malicious/incomplete/incompatible/cross-Workspace failure paths.
- [ ] Conduct periodic representative restore exercises after implementation.
- [ ] Update normative architecture documentation and `docs/decisions/README.md` only after acceptance.

No follow-up item authorizes Django initialization, application code, models, migrations, SQL, shell scripts, management commands, jobs, database configuration/connections, exports, archives, buckets, storage integrations, encryption keys, credentials, packages, backup/restore tooling, tests, production-data access, deployment, modification of the old Story Engine, or commit while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No backup script, export/import/restore code, database object, Django model/migration/command, job, storage integration, archive, key, credential, test, package, provider, retention value, RPO, RTO, storage location, or encryption algorithm is created or selected by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
