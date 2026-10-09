# Upload recovery journal (foundation)

SQLiteUploadAttemptStore provides a durable per-attempt state record: pending, completed, or failed. UploadAttemptRecovery can list pending attempts after a process restart without changing customer files. Attempts are keyed by random IDs and scoped to customer/project/filename. A second finalization is rejected.

**Not yet integrated:** The HTTP upload endpoint does not create or finalize journal entries. Therefore existing uploads are not yet recoverable through this journal. No automated retry, compensation, cleanup, or filesystem/SQLite atomic transaction exists. Pending entries alone cannot prove whether a file was written. Before enabling reconciliation, wire the journal into the upload boundary and define idempotent file verification and customer-safe recovery rules. Never delete a customer upload solely because a pending attempt exists.
