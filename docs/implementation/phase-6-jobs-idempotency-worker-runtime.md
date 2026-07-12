# Phase 6 Implementation Record: Jobs, Idempotency, and Worker Runtime

## Status

Completed on 2026-07-11.

This is an implementation record. ADR-0010 and ADR-0014 remain authoritative.

## Scope Delivered

Phase 6 adds the shared PostgreSQL-backed durable queue foundation: Job, Job Attempt, generic Idempotency Record, commit-coupled enqueue, skip-locked claiming, leases/heartbeats, bounded retries, cooperative cancellation, lease recovery, ambiguous-outcome quarantine, a worker command, restore quarantine, read-only admin, migration, and focused tests.

Only an allowlisted internal no-op handler exists. No search, import, AI, provider, backup, MFA, frontend, deployment, Redis, Celery, or external-broker feature was added.

## Job Schema

Job has UUIDv4 identity; optional protected Workspace; bounded job type/state/target category; optional target UUID; payload version; effect class; availability/start/finish timestamps; lease UUID/owner/expiry/heartbeat; attempt and maximum-attempt counts; cancellation timestamp; bounded result/failure/quarantine classifications; and operational timestamps.

It contains no body, JSON payload, manuscript, title, prompt, provider response, credential, URL/path, request, or exception field. Phase 6 has only `internal_noop`, payload version 1, and system/Workspace target categories. Effect class distinguishes internally idempotent work from future externally ambiguous work.

## Job Attempt Schema

Job Attempt has UUIDv4 identity; protected Job; unique Job-scoped attempt number; start/finish timestamps; bounded worker identifier; lease UUID; bounded running/succeeded/retryable/terminal/cancelled/ambiguous/lease-lost/quarantined outcome; bounded error category; and creation time.

Attempts contain no payload or raw exception. The default manager rejects update/delete. The narrow execution manager alone opens and finalizes attempts; completed evidence is never rewritten through ordinary paths.

## Generic Idempotency Record Schema

The generic record has UUIDv4 identity; optional protected Workspace; bounded web/operator/service caller class and non-secret caller reference; `enqueue_job` operation; bounded key; 64-hex fingerprint; pending/succeeded/failed-terminal state; optional protected resulting Job; bounded result/failure classifications; and timestamps.

Uniqueness spans Workspace, caller class/reference, operation, and key with PostgreSQL nulls treated as non-distinct, so global operations deduplicate correctly. Identical reuse returns the existing Job; changed fingerprint raises a visible conflict. Keys grant no authority. Scene Save Request remains a separate specialized record.

## State Machine

- `queued`: scheduled for a future `available_at`.
- `available`: ready for claim.
- `running`: actively leased.
- `retry_wait`: retryable failure or safe lease recovery awaiting availability.
- `cancellation_requested`: running lease remains active but handler must stop cooperatively.
- `succeeded`, `failed_terminal`, `cancelled`: terminal.
- `quarantined`: terminal pending explicit reconciliation; never automatically resumed.

Database checks constrain states, classifications, attempt bounds, key/fingerprint shapes, and lease presence. Only running/cancellation-requested rows may retain a lease.

## Job-Type Registry and Handler Context

The registry is a static mapping, not an import path. Unknown types fail before enqueue/execution. `internal_noop` receives only string Job/Workspace identities and a cancellation checkpoint. It performs no domain, file, network, SQL, shell, template, URL, or external effect.

Future handlers must extend the registry in reviewed code, use bounded context, revalidate authority/lifecycle, and remain idempotent. Job data can never select an arbitrary callable.

## Enqueue and Transactional Dispatch

`enqueue_job()` validates the allowlisted type and bounded classifications, key, caller, fingerprint, schedule, and retry limit. In one transaction it locks or reserves generic idempotency, creates the Job as the durable dispatch/outbox row, and marks the idempotency result succeeded. It never executes the handler.

Nested use inside a future authoritative transaction is commit-coupled: outer rollback removes both Job and idempotency reservation. Identical retry converges; changed semantic fingerprint fails. Delivery remains at least once and handlers must make effects idempotent.

## Claiming and Locking

`claim_jobs()` uses `SELECT FOR UPDATE SKIP LOCKED` through Django, filters due queued/available/retry-wait rows below their attempt limit, and orders by availability, creation, then UUID. A bounded batch is claimed in one short transaction.

Each claim atomically sets running state, lease identity/owner/expiry/heartbeat, increments attempt count once, and inserts exactly one attempt. Process-local locks are not used, and concurrent workers skip locked rows rather than taking a global queue lock.

## Leases and Heartbeats

The conservative default lease is 60 seconds; callers may choose 1–3600 seconds. Heartbeat requires the exact live lease and extends it in a short transaction. Finalization locks and verifies Job lease plus the open Attempt. An old worker receives `StaleJobLease` after expiry, recovery, restore quarantine, cancellation completion, or ownership replacement.

Lease expiry never proves an external effect did not occur. Internal-idempotent work may return to retry wait; future external-ambiguous work quarantines.

## Retry Formula

Default maximum attempts is 3, with an accepted service range of 1–20. Delay is `min(300 seconds, 5 * 2^(attempt-1) + jitter)`, where jitter is uniformly between zero and 25 percent of the uncapped base. Production uses system randomness; tests inject deterministic randomness.

Known retryable errors enter retry wait until the attempt budget is exhausted, then fail terminally. Terminal and unknown exceptions map to bounded permanent failure without storing exception text. Ambiguous outcomes always quarantine and never retry blindly.

## Cancellation

Queued/available/retry-wait Jobs cancel immediately. Running Jobs move to cancellation requested while retaining the lease. Handlers inspect cancellation at safe checkpoints; finalization then records cancelled. Cancellation does not roll back committed work or unsend external effects. Terminal Jobs cannot reopen.

## Execution and Reauthorization

Handlers run outside the claim transaction. Before execution, the service reloads Job state, validates the lease during finalization, and rechecks that an attached Workspace still exists and is active. The context supports later target/lifecycle/authority checks without treating enqueue authorization as permanent. Phase 6's system no-op needs no human Account or Workspace grant.

Service/worker identity is a bounded non-secret string and never becomes an Account, Workspace grant, or creative authority.

## Lease Recovery

Recovery locks expired running/cancellation rows and preserves the open attempt as lease-lost evidence. Cancellation completes as cancelled. Internal-idempotent work retries when budget remains or fails terminally at the limit. External-ambiguous work quarantines with lease-loss reason. Every recovered row loses its lease, preventing stale finalization.

## Worker Command

`run_worker` supports one-shot and continuous modes, bounded batch size (1–100), bounded idle sleep (0–60 seconds), and a validated generated/supplied worker ID. Each iteration recovers leases, claims due Jobs, executes outside claim transactions, finalizes by lease, and sleeps only when idle. Ctrl-C produces only `worker_stopped`.

Output contains iteration classifications and counts only—never Job payloads, private titles, keys, fingerprints, content, raw errors, URLs, paths, or credentials. There is no daemonization or production supervisor.

## Restore Quarantine

`quarantine_unfinished_jobs()` and its management command lock queued, available, running, retry-wait, and cancellation-requested Jobs; finish open attempts as quarantined; invalidate leases; and set bounded restore reason. Succeeded, failed, cancelled, and already-quarantined rows remain unchanged. No work resumes automatically.

This is a post-restore reconciliation primitive, not backup or restore tooling.

## Security, Provenance, and Evidence Boundaries

Normal Job execution belongs in Job and Job Attempt, not Security Event or Mutation Operation. The Phase 5 taxonomy is not broadened: restore quarantine is an explicit operator command with durable Job state, and no sensitive operator cancellation exists yet. Future high-impact operations may add reviewed Security Event types.

Mutation Operation remains accepted creative provenance. Scene Save Request remains HTTP-save idempotency. Generic Idempotency Record protects general enqueue. None is collapsed into another or grants authority.

## Admin and Logging

Job, Attempt, and generic Idempotency Record are staff-viewable read-only admin models with no add/change/delete. Broad lists omit keys, fingerprints, target UUIDs, lease IDs, caller references, and Workspace identifiers.

Worker output/log boundaries allow only bounded type/state/outcome/count/attempt/worker classifications. The implementation never logs keys, fingerprints, payloads, titles, content, raw exceptions, or private paths. No external telemetry vendor is added.

## Immutability and Residual Authority

Default managers and instance methods reject direct Job/Attempt/Idempotency updates and all ordinary deletes. Reviewed services use separate execution managers for state transitions. Protective foreign keys prevent cascades into Workspace or Job evidence.

The execution manager, raw SQL, migrations, alternate managers, and database ownership remain privileged bypasses. Production database-role separation and operational controls remain required; database triggers were not added.

## Migration

`src/jobs/migrations/0001_initial.py` creates exactly Job, Job Attempt, and Idempotency Record plus bounded checks, protective references, unique constraints, claim/recovery/lookup indexes, and UUID identities. It contains no data migration or sample Job.

The migration was not applied because no safe explicit `TEST_DATABASE_URL` was configured. SQLite was not used.

## Tests

Database-free tests cover exact private-data exclusions, concept separation, protected default managers, allowlisted registry, retry bounds, read-only admin, migration scope, and non-authoritative Job identity.

PostgreSQL-only tests cover commit/rollback dispatch, idempotent/conflicting enqueue, Workspace scope, schedule/terminal filtering, deterministic claims, multiple workers, heartbeat/stale lease, success/retry/terminal/ambiguous finalization, attempt budgets, cancellation, expired lease recovery, external ambiguity quarantine, restore quarantine, and command output.

Phase 6 adds 8 database-free cases and 13 PostgreSQL-only cases. Without `TEST_DATABASE_URL`, the complete repository suite reports 75 passed and 78 PostgreSQL cases skipped; integration tests never fall back to SQLite.

## Verification Commands

```console
uv sync --locked
python manage.py check --settings=strange_novelty.settings.local
python manage.py check --settings=strange_novelty.settings.test
python manage.py check --settings=strange_novelty.settings.production
python manage.py makemigrations --check --dry-run --settings=strange_novelty.settings.test
pytest
ruff check .
ruff format --check .
mypy manage.py src tests
git diff --check
```

## Known Limitations

- PostgreSQL integration was not executed without a safe configured test database.
- Only the internal no-op handler exists; there is no user-visible background feature.
- No scheduler, recurring-job model, dependency graph, batch/workflow engine, cleanup, or retention automation exists.
- No external-effect receipt/reconciliation table exists; ambiguous effects quarantine.
- No progress percentage or artifact model is added.
- No Security Event type is added for routine Job transitions.
- Worker supervision, concurrency sizing, database roles, shutdown deadlines, and operational alerting remain deployment work.

## Deferred Phase 7 and Later Work

Phase 7 may use this queue for rebuildable PostgreSQL search projections. Backup verification, legacy import, AI suggestions/provider effects, and production deployment follow later phases. Each must add explicit job types/handlers and reauthorization without weakening queue semantics.

## ADR Alignment

This implementation follows ADR-0010: PostgreSQL is the queue, Job is the outbox, delivery is at least once, handlers are idempotent, external work belongs outside long transactions, claims are leased, retries are bounded, ambiguity quarantines, restore never resumes blindly, and all evidence/idempotency/provenance concepts remain separate. It follows ADR-0014 through distinct web/worker roles, bounded output, safe configuration, and no deployment assumptions.
