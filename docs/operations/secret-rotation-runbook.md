# Secret Rotation Runbook

## General Boundary

Use external secret injection and purpose-specific credentials. Never record values in Git, images, commands, tickets, logs, metrics, archives, or this runbook. Record only secret category, key identifier, custodian, rotation time, and verification outcome.

## Django Signing Secret

Changing the signing secret invalidates signed values and may invalidate sessions. Enter maintenance, stop workers, preserve recovery evidence, rotate through the platform secret mechanism, explicitly delete all Django sessions, restart all roles together, and verify login/CSRF/logout. Multi-key overlap is deferred unless a reviewed Django mechanism is introduced.

## Database Credentials

Create or rotate the least-privileged role credential, update injected configuration, restart only the matching role, verify TLS/readiness, then revoke the old credential. Migration, runtime, backup, restore, and inspection credentials rotate independently. Never use a superuser for routine operation.

## Provider, Backup, Key, and Deployment Credentials

AI provider credentials do not yet exist. If later introduced, pause AI Jobs and reconcile ambiguous effects before rotation. Rotate backup credentials without colocating encryption keys; verify a new backup and isolated restore. Encryption-key material remains in separate custody; rotation requires decryptability and rollback testing. Rotate deployment tokens, verify immutable-image access, and revoke the old token.

## Failure and Rollback

Keep old credentials active only for the minimum tested overlap where supported. If verification fails, restore the previous injected reference, investigate without printing values, and do not revoke the last known recoverable credential. Review access evidence after every emergency rotation.
