# Interrupted recovery request inspection

Recovery attempts can be left `pending` after process crashes, audit errors, or journal CAS success followed by failure to record the outcome. A pending request must **never** be automatically replayed based only on the current journal state or a verified file.

`PendingRecoveryInspector` reads the existing legacy audit log but cannot correlate entries to a particular request: those entries carry operator identity, not request ID. Its results are diagnostic only.

`SQLiteRequestRecoveryAudit` stores new events with a request ID, owner scope and operator ID. `RequestRecoveryInspector` reads the exact request's events and current canonical publication assessment, but always returns `manual_review_required` for pending attempts, even if the final file currently verifies. A completed attempt returns its stored outcome, not proof that the file is currently unchanged.

The new request-scoped audit store is **not yet connected** to the active audited execution wrapper; therefore it will contain events only when explicitly written by a trusted caller. This is scaffolding, not an end-to-end recovery solution.

Authentication, operator authorization, durable operator review, and safe state repair remain future work. Existing local verification cannot guarantee remote SFTP semantics, immutable bytes, multi-host fencing, or atomicity between journal, audit, and filesystem. No production actions are performed.
