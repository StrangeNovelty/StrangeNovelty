# Release Notes

## Staging — 2026-07-18 — Complete Deck Collection

Classification: **Private Deck collection import and hosted workflow validation successful.**

### Release Identity

- Application commit: `08ee5db9f2059f9e5be37bae8501170f1a0ffd24`
- Web deployment: `f2358d73-a1bf-4103-b442-adbacdca48ae`
- Import batches: 2 committed

### Import Results

- The authoritative schema-v3 package validated locally and in staging with 2,148 accepted
  Cards, zero malformed records, duplicates, conflicts, or rejections, and no validate-only
  writes.
- The first committed import created 2,493 parent/native records and preserved the expected
  product totals: 840 Deck of Worlds Cards, 540 Lore Master's Deck Cards, and 768 Story
  Engine Cards.
- Supporting totals are 149 Rules, 28 Spreads or guided modules, 115 Spread positions, one
  Journal, six Journal sections, and 28 Journal prompts.
- Imported Card review states remain 1,998 pending, 30 needs correction, and 120 needing
  symbol review. Confidence totals remain 59 high, 1,400 medium, and 689 low.
- The required second committed import created and updated zero records, reported 2,493
  unchanged records, and preserved the synthetic custom Card, reviewed state, and favorite.

### Hosted Product Validation

- Authenticated Deck Library, Deck detail, pending inclusion, filters, search, Card detail,
  Review Workspace, missing-render behavior, Rules, Spreads, Journal, dashboard, and combined
  search checks passed without exposing host paths.
- A synthetic custom Card was approved and favorited; no imported commercial Card was
  approved or edited.
- Synthetic free and official Spread Draws passed with pending inclusion, deterministic seed
  behavior, required Categories, locking, redraw history, story-context snapshot, author
  notes, interpretation, and saved-history reopening.
- Release-fix PR #30 bound the Workspace before Draw form model validation, restoring
  coherent Work, Chapter, and Character context selection.
- The transient private package object was removed after import. The complete native
  collection and both ImportBatch records remain in staging for authenticated use.
- Production remains empty and untouched. AI remains disabled.

## Staging — 2026-07-18

Classification: **Hosted private storage release successful.**

### Release Identity

- Commit: `3db70cdbee4e592c8cb5a2401c38beb256870d9d`
- Migration deployment: `3f2f8fa4-7b05-4f0a-9ed7-b789a72cc117`
- Web deployment: `e65ede75-50a2-4a49-a915-592e247e5027`
- Worker deployment: `caf13347-f0bf-42e6-94a0-750e27df1edb`

### Results

- Staging now uses the private Railway S3-compatible bucket through environment variable
  references. Uploads and exports use separate prefixes; production configuration was not
  changed.
- Two additive storage-field migrations applied successfully. All 62 migrations are applied
  and none are pending.
- Authenticated synthetic Research upload, extraction, download, Note creation, and Chapter
  connection passed.
- Authenticated synthetic Artwork upload, inline preview, Collection membership, Character
  portrait connection, and dossier rendering passed.
- TXT, Markdown, HTML, DOCX, and PDF exports completed through the worker, retained MIME type,
  size, and checksum metadata, and passed authenticated download/content inspection.
- Missing-object, intentional generation-failure, retry, supersession, and export-history
  behavior passed. No partial object remained after the intentional generation failure.
- Research, Artwork, and all export formats remained downloadable after a web redeployment
  and from a new authenticated test session.
- Release-fix PR #28 corrected Collection membership form validation and added a focused
  authenticated POST regression.
- Synthetic `STAGING QA` storage fixtures remain for later release validation. AI remains
  disabled. Production remains empty and untouched.

## Staging — 2026-07-17

Classification: **Grouped creative-product staging release successful.**

### Release Identity

- Commit: `c6c4288c9f2f255a176b92b5badfe273d0957465`
- Migration deployment: `7f53a216-863f-446d-9857-37e7b067e936`
- Web deployment: `c05d286b-747f-4f02-a378-ecbb571c8b41`
- Worker deployment: `37fc9566-4848-4ee8-9877-c0f82ea7d7b8`

### Results

- Twenty-four additive migrations across ten apps applied successfully; all 60 migrations
  are applied and none are pending.
- Staging web liveness, readiness, static assets, and worker readiness passed. Maintenance
  mode is disabled and the Job queue is empty.
- MFA-protected rendered-page smoke tests passed for every primary product destination using
  a synthetic test session. The physical WebAuthn login ceremony was not exercised.
- A clearly labelled synthetic QA Work was retained with Chapter, immutable Scene revisions,
  Beat, Scene Brief, pacing, and planning-snapshot records for future release checks.
- AI remains disabled. Routine smoke testing stopped at the provider-neutral application
  shell as required by the staging synthetic-account policy.
- Private file storage remains the development filesystem backend. Metadata-only Library
  workflows are available, but durable hosted uploads and generated exports remain a known
  staging limitation until private object storage is configured.
- No product defects requiring a release-fix PR were found. The maintenance-mode worker exit
  observed during rollout was the expected fail-closed behavior; the worker was deployed
  successfully after maintenance was disabled.
- Production remains empty and untouched.

## Staging — 2026-07-13

Classification: **Staging release successful with authenticated smoke-test exception.**

### Release Identity

- Commit: `f2ce2d5d58a4c7a9c26fbe1a3ad90af68c28f8c2`
- Migration deployment: `539cbef0-1534-4151-b957-7ad24475d251`
- Web deployment: `5f5ae1f0-c4a9-450b-b7fd-f7fc817e271b`
- Worker deployment: `14effeb1-a0a1-474c-a0c5-a78dfd15212f`

### Results

- Staging migration, web, and worker services are healthy.
- Maintenance mode is disabled.
- All 36 migrations are applied and zero are pending.
- The application stylesheet is present in the image, static-files manifest, collected
  output, and successful public HTTP response.
- The worker is ready and idle with no unexpected queue or quarantine growth.
- AI is disabled.
- Unauthenticated smoke tests passed.
- Authenticated smoke tests are deferred because no approved staging credential-retrieval
  path existed during this release.
- The existing bootstrap-linked staging owner account and its approved fixtures were
  formally designated as synthetic after the release. This does not retroactively complete
  the deferred authenticated checks.
- Credential discovery changed no accounts, credentials, Railway state, Git state, or
  production resources.
- Production remains untouched.

### Follow-Up Resolution

**Document staging synthetic-account credential custody and recovery.**

The approved policy is documented in
`docs/operations/staging-synthetic-account-runbook.md`. Beverly Toole is the accountable
owner and primary custodian; no backup custodian is assigned. Beverly's existing password
manager is authoritative. The policy requires primary and separately controlled backup
WebAuthn factors, separately restricted recovery codes, 90-day and event-driven password
rotation, 12-month audit retention, and request-shell-only AI smoke testing without invoking
a provider.

Password loss stops the workflow and requires a separately reviewed staging-only reset
procedure. Credentials and private authentication or fixture material remain prohibited from
Railway variables, repository files, shell history, logs, screenshots, HAR files, tickets,
chat, and release reports.

## Staging — 2026-07-18 — Real AI provider validation

Classification: **OpenRouter task routing enabled and synthetic creative workflows validated.**

### Release Identity

- Application commit: `dca16095a0bd260e368e805976bd33f4ce694c73`
- Migration deployment: `701da44b-7c76-44dd-9f30-0eda2646c3cd`
- Web deployment: `87d637b6-7bff-4f82-a59d-e620381bc663`
- Worker deployment: `eed2e0c5-0714-4b8e-9046-7bcb889a588a`

### Results

- The staging OpenRouter adapter is enabled with environment-configurable task routing:
  Aion 3.0 for writing, GLM 5.2 as its retryable alternate, GPT-5 Mini for outlining and
  analysis, and Claude Sonnet 4.5 for brainstorming. `AI_MODEL` remains the fallback.
- Synthetic Story Chat, Chapter outline, Scene Brief, Character, Ability, Monster, Deck,
  Continuity, Timeline, Voice, and editorial requests reached reviewed suggestion states.
- Explicit Chapter, immutable Scene, Creature, Voice Profile, and planned Timeline Event
  application/conversion paths retained provenance. Stale Scene sources were blocked.
- One controlled malformed structured response was retained as failed; the repaired prompt
  contract then passed. Local fake-provider timeout, cancellation, malformed-output, retry,
  privacy, Job, and stale-source regressions remain green.
- Provider usage metadata supplied token counts but no cost value during this validation.
- The bounded `STAGING AI QA` fixture remains for later regression checks. AI output remains
  review-first, non-canon, and incapable of silently mutating story records.
- Change the default or routed model through the documented environment variables. Disable
  provider calls by setting `AI_ENABLED=false`; no credential belongs in Git or documentation.
- Staging is healthy. Production remains empty and untouched.
