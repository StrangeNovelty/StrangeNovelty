# Development Handoff

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
