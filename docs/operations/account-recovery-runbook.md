# Account Recovery Runbook

This procedure recovers MFA access when the existing password remains available but normal
WebAuthn and recovery-code access cannot restore the owner. For the staging synthetic owner,
first follow the custody and authorization requirements in
`docs/operations/staging-synthetic-account-runbook.md`.

Confirm host control, enter maintenance mode, pause workers, preserve bounded evidence, and
take a verified database backup.

1. Identify Account and Workspace UUIDs from protected operational records; email alone is insufficient.
2. Confirm exactly one active owner Grant and document the reason without secrets.
3. Run `python manage.py recover_owner_access --account <account-uuid> --workspace <workspace-uuid> --confirm` with the operator role. Never pass a password, code, or key.
4. The command revokes sessions, factors, and unused codes and opens a 30-minute re-enrollment state. It does not create an owner or alter authority.
5. The owner signs in with the existing password, enrolls a primary and separately
   controlled backup WebAuthn factor, generates replacement recovery codes, and reviews
   sessions. Store staging recovery codes only in the separate restricted password-manager
   item. Rotate the password through the protected flow after recovery.
6. Run private-content readiness checks, rotate exposed secrets, review evidence, then leave maintenance mode.

Stop on ambiguous identity. This command does not reset a lost password. If the existing
password is unavailable, stop and require a separately reviewed staging-only password-reset
procedure. Manual database edits are prohibited. There is no email reset, SMS fallback,
permanent bypass, or universal recovery credential.
