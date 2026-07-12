# PostgreSQL Role Boundaries

Production uses TLS and separate externally managed credentials. Exact grants are reviewed against generated migrations and backup tooling before execution; this document is guidance, not executable SQL.

- Migration role: owns or may alter the application schema; used only by the serialized release task.
- Runtime web role: required application reads/writes only; not owner, superuser, role creator, or database creator.
- Runtime worker role: initially may share the same restricted grants as web because Jobs and domain handlers touch the same tables, but uses a separate credential and connection budget.
- Backup role: least read/backup capability required by the selected PostgreSQL-native backup method; cannot serve the application.
- Restore role: elevated only inside an isolated empty recovery target; cannot activate traffic.
- Inspection role: read-only, time-bounded operational diagnosis; direct private-content access remains exceptional and audited.

Set bounded connection pools, connect timeout, statement timeout, and lock timeout. Serialize migrations with operator/release coordination. Never put passwords in command arguments; use the platform secret boundary or protected PostgreSQL password-file mechanism. Routine roles must never be PostgreSQL superusers or cluster-wide owners.
