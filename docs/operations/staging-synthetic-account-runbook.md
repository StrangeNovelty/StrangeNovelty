# Staging Synthetic Account Runbook

## Purpose and Scope

This runbook governs custody and use of the Strange Novelty staging synthetic owner
account. It applies only to staging and does not authorize access to or changes in
production.

The existing bootstrap-linked staging owner account is the designated staging synthetic
owner account. Its Workspace and approved fixtures are test-only synthetic data. Do not
record its username, Account ID, Workspace ID, fixture names, or fixture content in this
runbook or in release evidence.

Beverly Toole is the accountable owner and primary custodian. No backup custodian is
currently assigned. Adding one requires Beverly's approval, password-manager access review,
factor handoff, and an audit record.

## Credential and Factor Custody

Beverly's existing password manager is the authoritative credential store. Keep the login
URL, protected login identifier, unique generated password, last-rotation date, and next
rotation date in a staging-only item named `Strange Novelty — Staging Synthetic Owner`.
Do not duplicate the password into another operational system.

Maintain two WebAuthn factors:

- one primary factor for routine authentication; and
- one separately controlled backup factor, stored separately from the primary factor and
  available only for recovery.

Record factor ownership and storage location in the password manager without recording
factor secrets. Until a backup custodian is assigned, Beverly retains custody of both
factors but must keep the backup physically or logically separate from the primary.

Store recovery codes in a separate restricted password-manager item named
`Strange Novelty — Staging Synthetic Owner Recovery`. Access to the login item does not by
itself authorize access to the recovery item. Recovery codes are emergency credentials and
must not be used for routine smoke tests.

Credentials, recovery codes, cookies, tokens, and private fixture content must never be
stored in Railway variables, repository files, shell history, logs, screenshots, HAR files,
tickets, chat, or release reports. Do not put credentials in command arguments, environment
variables, clipboard managers, terminal transcripts, or browser synchronization.

## Authorization and Audit

Routine use requires an approved staging release or smoke-test record. Before access, record
the operator, Beverly's approval or the standing procedure being used, purpose, staging
release identity, and start time. The operator may use the credential only for the approved
staging checks.

Retain access, smoke-test, rotation, recovery, factor-custody, and password-manager audit
records for 12 months. Records may contain:

- operator and approving owner;
- timestamp, staging scope, release identity, and reason;
- password-manager item reference, but not its values;
- authentication-factor class used;
- pass/fail classifications and bounded security-event types; and
- rotation, recovery, factor replacement, or session-revocation actions.

Do not record identifiers, credentials, recovery material, cookies, tokens, fixture content,
search text, or private response bodies. Review the password-manager access audit and the
application's bounded security events after each use.

## Routine Login and Authenticated Smoke Test

Routine login is not recovery and must not consume a recovery code.

1. Confirm the intended release is active in staging, maintenance is disabled, health and
   worker readiness pass, and AI remains disabled.
2. Confirm the operator approval and open the bounded audit record.
3. Use a managed workstation and a temporary private browser profile. Disable browser sync,
   screenshots, screen recording, and network capture.
4. Open the staging login URL from the password-manager item and use password-manager
   autofill. Do not reveal, copy into notes, or type the credential into a shell.
5. Complete MFA with the primary WebAuthn factor.
6. Open the Workspace dashboard and verify the approved synthetic Workspace loads.
7. Open the Scene list and the existing approved synthetic Scene. Do not edit or save it.
8. Run the approved synthetic Search and verify the expected synthetic result without
   recording the query or result content.
9. Open the AI request shell from the synthetic Scene and verify its authorization and UI
   boundary. Do not submit a request, create an AI record, or invoke a fake or external
   provider. Routine AI smoke testing ends at this shell.
10. Verify private responses, including Workspace, Scenes, Search, and the AI request shell,
    have restrictive cache headers including `Cache-Control: no-store`. Do not save a HAR
    file or response body.
11. Submit the application's logout form.
12. Revisit private routes and confirm they redirect to login.
13. Close and delete the temporary browser profile. Confirm expected bounded login, MFA,
    and logout security events and record only pass/fail results.

Stop and report a failed gate without exposing private content. Do not change fixtures,
accounts, providers, deployments, or production to make a smoke test pass.

## Password Rotation

Rotate the password every 90 days and immediately after suspected exposure, account
recovery, or a custodian change. Routine password rotation requires the current password and
recent MFA; it is not an MFA-recovery procedure.

1. Open an approved staging rotation record and confirm Beverly's authorization.
2. Sign in using password-manager autofill and the primary WebAuthn factor.
3. Use the protected account password-change flow after establishing recent MFA assurance.
4. Generate and autofill a unique replacement using the password manager.
5. Update the authoritative login item only after the application confirms the change.
6. Log out, then verify a fresh login and WebAuthn challenge with the new password.
7. Review sessions and revoke any that are unexpected.
8. Verify the bounded password-change and session security events. Record the rotation date,
   next due date, operator, reason, and outcome without recording either password.

If any step is ambiguous, stop. Do not use the bootstrap command, a database edit, or an
unreviewed reset mechanism.

## MFA Recovery

MFA recovery applies only when the password remains available.

If the primary factor is unavailable but the separately controlled backup factor works, use
the backup factor, replace the lost factor, and audit the factor change. Rotate the password
immediately if exposure is possible.

If neither WebAuthn factor is available but a recovery code is available:

1. Obtain explicit recovery approval and retrieve one code from the restricted recovery
   item without copying it into an operational record.
2. Sign in with the existing password and consume one recovery code.
3. Enroll and verify replacement primary and separately controlled backup WebAuthn factors.
4. Revoke lost or unaccounted-for factors.
5. Generate a complete replacement recovery-code set and replace the restricted recovery
   item; do not retain the old set.
6. Rotate the password, review sessions, and verify the bounded recovery, factor, code,
   password-change, and session events.
7. Record the reason and outcome without recording credential material.

If the password is available but all MFA factors and recovery codes are lost, follow the
account-recovery runbook. That procedure requires separately approved Railway and account
state changes, maintenance mode, a paused worker, a verified backup, protected identity
confirmation, and time-bounded MFA re-enrollment.

## Password-Loss Recovery

Password loss is not MFA recovery. Stop the workflow if the authoritative password-manager
credential is unavailable or fails and no verified current password exists.

The owner bootstrap and MFA-recovery commands do not reset a password. Manual database edits
are prohibited. Recovery requires a separately designed and reviewed staging-only
password-reset procedure with explicit approval, bounded identity verification, session and
factor review, audit evidence, and post-reset rotation. Do not improvise that procedure from
this runbook.

## Custody Review

Review custody at least at every 90-day password rotation and whenever a custodian, factor,
or password-manager access policy changes. Confirm that both WebAuthn factors work, remain
separately controlled, recovery codes remain restricted, audit records remain available for
12 months, and no unauthorized copies exist.
