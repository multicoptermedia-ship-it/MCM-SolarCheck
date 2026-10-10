# Audited explicit local publication recovery

The opt-in `AuditedPublicationRecovery` wrapper requires a nonempty operator identifier supplied by an **already authenticated and authorized** trusted caller. It durably records `requested` before invoking explicit reconciliation and records the returned decision afterward. Denials are audited too. If the intent audit fails, no recovery transition is attempted. If the outcome audit fails, the error propagates; the caller must not interpret it as a successful response because the journal may already have changed.

`RecoveryAuditInspection` restricts audit reads by canonical transfer ownership. The audit database is append-only at the application API level, **not** protected from direct SQLite mutation by administrators.

Limitations: Operator authentication and authorization are not implemented by this wrapper; it is not wired to public HTTP endpoints. Audit intent, journal CAS, and audit outcome are separate transactions, so crash windows and unresolved intents remain possible. The preexisting double-check and process-local lock do not provide distributed fencing or immutable source files. Future work should add durable idempotency, reconciliation of pending audit intents, operator access controls, and safe handling of multiple hosts. No IONOS SFTP or deployment was performed.
