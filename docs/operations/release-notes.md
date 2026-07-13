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
