# Development Handoff

## Current Staging Deck State — 2026-07-18

Classification: **Complete private Deck collection imported and validated.**

Staging web runs application commit `08ee5db9f2059f9e5be37bae8501170f1a0ffd24`
in deployment `f2358d73-a1bf-4103-b442-adbacdca48ae`. Liveness and readiness return
HTTP 200. The existing migration and worker deployments remain healthy because the focused
Draw form repair required only the web role.

The staging Workspace contains all 2,148 imported Cards: 840 Deck of Worlds, 540 Lore
Master's Deck, and 768 Story Engine. It also contains 149 Rules, 28 Spreads or modules, 115
Spread positions, one Journal, six sections, and 28 prompts. Imported review states are
1,998 pending, 30 needs correction, and 120 needing symbol review; no imported Card was
approved during smoke testing.

Both committed ImportBatch records are clean. The second import reported zero created or
updated records and 2,493 unchanged records while preserving the approved/favorited
synthetic custom Card. Authenticated Library, review, guidance, free Draw, official Spread,
context snapshot, interpretation, search, and dashboard checks passed. Release-fix PR #30
corrected Draw creation with coherent story context. The transient package object was
removed; the authoritative audit remains outside the repository. AI is disabled, and
production remains empty and untouched.

## Current Staging Release — 2026-07-18

Classification: **Hosted private storage release successful.**

Staging runs commit `3db70cdbee4e592c8cb5a2401c38beb256870d9d` with these
deployments:

| Service | Deployment ID |
| --- | --- |
| `staging-migration` | `3f2f8fa4-7b05-4f0a-9ed7-b789a72cc117` |
| `staging-web` | `e65ede75-50a2-4a49-a915-592e247e5027` |
| `staging-worker` | `caf13347-f0bf-42e6-94a0-750e27df1edb` |

All 62 migrations are applied with none pending. Liveness and readiness return HTTP 200,
and the worker is healthy and idle. Staging uses a private Railway S3-compatible bucket via
environment variable references; production configuration is unchanged.

Authenticated synthetic Research upload and extraction, Artwork preview and Character
portrait use, and TXT, Markdown, HTML, DOCX, and PDF export generation/download all passed.
The stored objects remained available after web redeployment and in a new authenticated
test session. Missing objects, generation failure, retry, supersession, and retained export
history also passed. Release-fix PR #28 corrected Collection membership form validation.
The bounded `STAGING QA` fixtures remain for future release validation. AI remains disabled,
and production remains empty and untouched.

## Current Staging Release — 2026-07-17

Classification: **Grouped creative-product staging release successful.**

Staging runs commit `c6c4288c9f2f255a176b92b5badfe273d0957465` with these
deployments:

| Service | Deployment ID |
| --- | --- |
| `staging-migration` | `7f53a216-863f-446d-9857-37e7b067e936` |
| `staging-web` | `c05d286b-747f-4f02-a378-ecbb571c8b41` |
| `staging-worker` | `37fc9566-4848-4ee8-9877-c0f82ea7d7b8` |

All 60 migrations are applied with none pending. Web liveness, readiness, static assets,
and worker readiness pass; maintenance is disabled and the Job queue is empty. Protected
rendered-page checks passed across the grouped shell, writing, character, world, continuity,
timeline, Deck, AI, Library, Publishing, Create, Help, and Search destinations using a
synthetic test session. The physical WebAuthn login ceremony was not exercised.

One `STAGING QA` synthetic Work and its bounded writing records remain for future release
validation. AI is disabled. Staging private files still use the development filesystem
backend, so durable hosted uploads and export retention remain unavailable until private
object storage is configured. Production remains empty and untouched.

## Current Staging Release

Classification: **Staging release successful with authenticated smoke-test exception.**

Staging runs commit `f2ce2d5d58a4c7a9c26fbe1a3ad90af68c28f8c2` with these
deployments:

| Service | Deployment ID |
| --- | --- |
| `staging-migration` | `539cbef0-1534-4151-b957-7ad24475d251` |
| `staging-web` | `5f5ae1f0-c4a9-450b-b7fd-f7fc817e271b` |
| `staging-worker` | `14effeb1-a0a1-474c-a0c5-a78dfd15212f` |

All three services are healthy. Maintenance is disabled, the worker is ready and idle,
and AI remains disabled. The migration gate reported all 36 migrations applied with zero
pending. The application stylesheet was verified in the image source tree, static-files
manifest, collected output, and public HTTP response.

Unauthenticated smoke tests passed. Authenticated Workspace, Scene, Search, AI-shell,
private-cache, and logout smoke tests remain deferred because there is no approved staging
credential-retrieval path at the time of this release. The historical exception remains even
though a custody policy was approved afterward; those authenticated checks were not rerun as
part of the completed release.

Credential discovery was read-only. It changed no accounts, credentials, Railway state, Git
state, or production resources. Production remains untouched.

## Synthetic Account Policy Follow-Up

The existing bootstrap-linked staging owner account is now formally designated as the
staging synthetic owner account, and its Workspace and approved fixtures are test-only
synthetic data. Beverly Toole is the accountable owner and primary custodian. No backup
custodian is assigned.

The operational procedure is documented in
`docs/operations/staging-synthetic-account-runbook.md`. It requires Beverly's existing
password manager, primary and separately controlled backup WebAuthn factors, recovery codes
in a separate restricted item, 90-day password rotation, immediate event-driven rotation,
and 12-month audit retention. Routine AI smoke testing stops at the AI request shell and may
not invoke a provider.

Authenticated smoke testing may resume only after the runbook's operational preflight is
satisfied, including custody of both factors and the separate recovery item. Password loss
still requires a separately reviewed staging-only reset procedure; manual database edits are
prohibited.
