# Recovery concurrency and audit foundation

Explicit local reconciliation now uses a process-local nonblocking lock per transfer/customer/project and repeats the complete owner, reservation and file integrity assessment before changing the journal state. A changed result fails closed. The SQLite journal transition remains conditional on the expected prior state.

`SQLiteRecoveryAudit` provides a separate owner-scoped, append-only event recording interface for an authenticated operator workflow. **It is not automatically connected to the recovery action.** A future trusted orchestration layer must enforce operator authorization and define a fail-closed audit/write ordering policy.

Limits: Process-local locks do not coordinate multiple processes or hosts. Two hashes do not eliminate a time-of-check/time-of-use race or prevent a concurrent writer modifying the hard-linked source. Audit events and journal changes are not transactional together. Do not expose this prototype as automatic recovery, remote SFTP fencing, or production-safe release. No IONOS connection or billable workers are enabled.
