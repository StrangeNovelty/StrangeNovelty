# Release Notes

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
