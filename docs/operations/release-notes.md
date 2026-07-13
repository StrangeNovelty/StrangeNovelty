# Release Notes

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
  path exists.
- One existing owner account appears suitable for the synthetic checks, but the schema does
  not prove that it is a synthetic account.
- Credential discovery changed no accounts, credentials, Railway state, Git state, or
  production resources.
- Production remains untouched.

### Follow-Up

**Document staging synthetic-account credential custody and recovery.**

The approved procedure must identify an external password-manager location, named account
ownership and custody, WebAuthn or recovery-code custody, rotation and recovery steps, and a
bounded audit trail. Credentials must never be stored in Railway variables, repository files,
shell history, logs, or release reports.
