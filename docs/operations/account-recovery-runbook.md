# Account Recovery Runbook

Use only when password plus normal MFA/recovery access cannot restore the owner. Confirm host control, enter maintenance mode, pause workers, preserve bounded evidence, and take a verified database backup.

1. Identify Account and Workspace UUIDs from protected operational records; email alone is insufficient.
2. Confirm exactly one active owner Grant and document the reason without secrets.
3. Run `python manage.py recover_owner_access --account <account-uuid> --workspace <workspace-uuid> --confirm` with the operator role. Never pass a password, code, or key.
4. The command revokes sessions, factors, and unused codes and opens a 30-minute re-enrollment state. It does not create an owner or alter authority.
5. The owner signs in with the existing password, enrolls WebAuthn, generates recovery codes, and reviews sessions. Change the password through the protected flow if compromise is suspected.
6. Run private-content readiness checks, rotate exposed secrets, review evidence, then leave maintenance mode.

Stop on ambiguous identity. There is no email reset, SMS fallback, permanent bypass, or universal recovery credential.
