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
credential-retrieval path. One existing owner account appears suitable for synthetic staging
checks, but the schema does not prove that the account is synthetic.

Credential discovery was read-only. It changed no accounts, credentials, Railway state, Git
state, or production resources. Production remains untouched.

## Follow-Up

### Document staging synthetic-account credential custody and recovery

Define and approve an operational procedure that includes:

- an approved external password-manager location;
- named ownership and custody for the staging account;
- named custody for its WebAuthn factor or recovery codes;
- password, MFA, rotation, and recovery procedures;
- a bounded audit trail for access, rotation, and recovery; and
- an explicit prohibition on storing credentials in Railway variables, repository files,
  shell history, logs, or release reports.

Do not resume authenticated staging smoke tests until this custody and recovery procedure is
approved and the existing account is confirmed as the dedicated synthetic staging account.
