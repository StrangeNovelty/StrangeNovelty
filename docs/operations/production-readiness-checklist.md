# Production Readiness Checklist

## Blocking Gate

- [ ] WebAuthn and bounded TOTP fallback are implemented and tested.
- [ ] `MFA_ENFORCED=true` with a dedicated injected Fernet key, exact RP ID, and HTTPS origin.
- [ ] An active owner has an active WebAuthn credential, unused recovery codes, and no open recovery enrollment.
- [ ] Database-backed `verify_production_readiness --private-content` passes; this does not replace the remaining checks below.
- [ ] Private-content production approval is recorded. Password-only authentication is non-production only.

Until all three are complete, production use with real private manuscript content is prohibited.

## Release and Configuration

- [ ] Immutable image digest, source commit, build identity, configuration schema, and dependency lock are recorded.
- [ ] Production data/secrets are isolated; external injection is configured; no fake AI adapter is enabled.
- [ ] Runtime roles are non-root and separated; routine database roles are not owners/superusers.
- [ ] TLS proxy and PostgreSQL TLS are verified; request/process/resource limits are set.
- [ ] Static manifest exists; deploy/system checks and migration plan pass.

## Recovery and Operations

- [ ] Multiple encrypted backup generations exist in external storage.
- [ ] Integrity verification and a representative isolated restore test pass.
- [ ] Session invalidation, Job/import/AI quarantine, search reset, and controlled activation are exercised.
- [ ] Deployment, rollback, incident, rotation, maintenance, break-glass, and backup runbooks are reviewed.
- [ ] Web/worker readiness, synthetic owner workflows, alerts, bounded logging, and capacity checks pass.

## Alert Conditions

Define deployment-specific thresholds and protected notification routes for web/worker unavailability, readiness failure, generic server-error rate, PostgreSQL connectivity/capacity, migration failure, backup failure/staleness, restore-verification failure, Job backlog/expired leases/terminal/quarantine growth, authentication anomalies, configuration/secret failure, storage exhaustion, search backlog, import quarantine, and AI quarantine. Alerts contain no private content or high-cardinality identifiers.
