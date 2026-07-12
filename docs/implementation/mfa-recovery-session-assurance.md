# MFA, Recovery, and Session Assurance

## Boundary and dependencies

Version 1 uses `webauthn` 2.x for WebAuthn verification, `pyotp` 2.x for TOTP, and `cryptography` 46.x Fernet authenticated encryption for TOTP secrets and challenges. Hosted identity, provider SDKs, custom cryptography, and attestation trust are unused.

Password is the first factor. With `MFA_ENFORCED=true`, password success creates password-only assurance and redirects to `/mfa/`; centralized middleware permits only MFA, logout, limited security enrollment, health, and administration boundaries until assurance is upgraded. Workspace Grants remain separate authorization.

## Records

- `WebAuthnCredential`: UUID, protected Account, unique credential ID, public key, sign count, bounded classifications/label, state, and timestamps. No private key or raw response is retained.
- `TOTPCredential`: UUID, protected Account, Fernet ciphertext, bounded label, fixed SHA-1/six-digit/30-second parameters, replay counter, pending/active/revoked state, expiry and use timestamps.
- `RecoveryCode`: UUID, Account, generation UUID, one-way password hash, and use/revocation timestamps. Plaintext is shown once.
- `SessionAssurance`: UUID, Account, HMAC session digest, password/MFA/recent timestamps, bounded level/method, last-seen and revocation facts. No raw session key, IP, or user agent.
- `AuthenticationChallenge`: encrypted random challenge bound to Account, session digest, purpose, expiry, and one-time consumption.
- `AuthenticationThrottle`: keyed HMAC scope and bounded PostgreSQL-backed category/window/count/block.
- `RecoveryEnrollment`: expiring one-time operator-recovery state.

## Policy and flows

WebAuthn requires user verification, explicit RP ID and one HTTPS origin in production, `none` attestation behavior, and a five-minute server-side single-use challenge. Counter non-increase for a counter-capable credential fails safely.

TOTP is fallback only. The dedicated injected Fernet key is separate from `SECRET_KEY`; production fails closed when enforcement lacks valid configuration. Pending enrollment expires after ten minutes and requires confirmation. A one-step clock window is accepted and a used time-step cannot replay.

Ten high-entropy recovery codes require an active factor. Regeneration revokes older unused codes; row locking atomically consumes one code after password authentication. MFA assurance has a 12-hour absolute bound and recent authentication is five minutes; ordinary activity does not extend it. Password change requires recent assurance, uses Django validation, rotates the session, and revokes other assurances.
When freshness expires, Version 1 requires signing out and completing password plus MFA again; there is no hidden activity-based refresh or remembered-device shortcut.

Password, WebAuthn, TOTP, and recovery failures use keyed, database-backed attempt windows (five attempts in ten minutes, followed by a fifteen-minute block). This is a bounded defense, not absolute brute-force prevention. Expired throttle/challenge cleanup is an operator maintenance concern in this release; no scheduler or Redis dependency is introduced.

`recover_owner_access --account UUID --workspace UUID --confirm` validates one active owner Grant, revokes sessions/factors/codes, and creates a 30-minute re-enrollment state. It accepts no password argument and email alone never establishes identity.

## Operational boundaries

Bounded Security Events cover MFA outcomes, factor enrollment/use/anomaly, recovery, session revocation, password change, throttling, and operator recovery without storing authentication material. MFA models are read-only in admin with secret fields excluded. Pages are private/no-store, CSRF protected, escaped, keyboard usable, and use local assets.

Portable archives exclude authentication state. Disaster recovery deletes sessions, revokes assurances and pending recovery, consumes challenges, and revokes pending TOTP. Maintenance permits login, MFA, logout, and security flows while blocking ordinary mutations.

Private-content readiness requires valid enforcement configuration plus an active owner Grant, active WebAuthn credential, unused recovery codes, no unresolved recovery state, and current migrations. Other Phase 11 operational items remain independent launch criteria.

Migrations are `accounts/0002`–`0003` and `security_events/0002`–`0004`. PostgreSQL integration requires explicit `TEST_DATABASE_URL`. This implements ADR-0005 and ADR-0014 without email/SMS recovery, trusted-device bypass, or external identity.
